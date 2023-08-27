import asyncio
import json
import logging

from aio_pika import IncomingMessage, Message, connect
from aio_pika.abc import AbstractQueue
from roster_agent_runtime import constants, errors, settings
from roster_agent_runtime.util.async_helpers import make_async

logger = logging.getLogger(constants.LOGGER_NAME)


class RabbitMQClient:
    def __init__(
        self,
        host: str = settings.RABBITMQ_HOST,
        port: int = settings.RABBITMQ_PORT,
        username: str = settings.RABBITMQ_USER,
        password: str = settings.RABBITMQ_PASSWORD,
        vhost: str = settings.RABBITMQ_VHOST,
    ):
        self.connection = None
        self.channel = None
        self.callbacks = {}
        self.active_queues = {}
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.vhost = vhost

    async def setup(self, retries: int = 10, delay: float = 2):
        for i in range(retries):
            try:
                await self.connect()
                logger.debug("(setup_rabbitmq): Connected to RabbitMQ")
                return
            except OSError as e:
                logger.debug("(setup_rabbitmq): Could not connect to RabbitMQ")
                if i < retries - 1:
                    logger.debug("(setup_rabbitmq): Retrying in %s seconds", delay)
                    await asyncio.sleep(delay)
                else:
                    logger.debug("(setup_rabbitmq): No more retries")
                    raise errors.SetupError(
                        f"Could not connect to RabbitMQ after {retries} retries"
                    ) from e

    async def teardown(self):
        try:
            await self.disconnect()
        except Exception as e:
            logger.debug(
                "(teardown_rabbitmq) Error while disconnecting from RabbitMQ: %s", e
            )
            raise errors.TeardownError(
                f"Error while disconnecting from RabbitMQ."
            ) from e

    async def connect(self):
        self.connection = await connect(
            f"amqp://{self.username}:{self.password}@{self.host}"
        )
        self.channel = await self.connection.channel()

    async def disconnect(self):
        if self.channel:
            await self.channel.close()
        else:
            logger.warning("RabbitMQ channel is not open, cannot close")
        if self.connection:
            await self.connection.close()
        else:
            logger.warning("RabbitMQ connection is not open, cannot close")

    async def _publish(self, queue_name: str, message: bytes):
        await self.channel.default_exchange.publish(
            Message(body=message), routing_key=queue_name
        )

    async def publish(self, queue_name: str, message: str):
        await self._publish(queue_name, message.encode())

    async def publish_json(self, queue_name: str, message: dict):
        await self._publish(queue_name, json.dumps(message).encode())

    async def register_callback(self, queue_name: str, callback: callable):
        # If callback is sync, wrap it into an async function.
        if not asyncio.iscoroutinefunction(callback):
            callback = make_async(callback)

        # Register the callback.
        # NOTE: Callbacks must accept single string argument (decoded message body).
        if queue_name not in self.callbacks:
            self.callbacks[queue_name] = []
        self.callbacks[queue_name].append(callback)

        # If a consumer hasn't been set up for this queue yet, set it up.
        if queue_name not in self.active_queues:
            consumer_tag, queue = await self._setup_queue_consumer(queue_name)
            self.active_queues[queue_name] = (consumer_tag, queue)

    async def _setup_queue_consumer(
        self, queue_name: str
    ) -> tuple[str, "AbstractQueue"]:
        queue = await self.channel.declare_queue(queue_name)
        consumer_tag = await queue.consume(self._create_message_handler(queue_name))
        return consumer_tag, queue

    def _create_message_handler(self, queue_name: str):
        async def handle_message(message: IncomingMessage):
            # Context manager handles acknowledgement
            async with message.process():
                callbacks = self.callbacks.get(queue_name, [])
                await asyncio.gather(
                    *[callback(message.body.decode()) for callback in callbacks],
                    return_exceptions=True,
                )

        return handle_message

    async def deregister_callback(self, queue_name: str, callback: callable):
        # Remove the callback from the queue's callback list.
        if queue_name in self.callbacks and callback in self.callbacks[queue_name]:
            self.callbacks[queue_name].remove(callback)

        # If it's the last callback for the queue, stop consuming from the queue.
        if not self.callbacks.get(queue_name):  # No more callbacks for this queue.
            consumer_tag, queue = self.active_queues.pop(queue_name, None)
            if consumer_tag:
                await queue.cancel(consumer_tag)

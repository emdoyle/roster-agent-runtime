import asyncio
import json
from typing import Optional

from roster_agent_runtime.agents import AgentHandle
from roster_agent_runtime.agents.pool import AgentPool
from roster_agent_runtime.informers.events.spec import RosterResourceEvent
from roster_agent_runtime.informers.roster import RosterInformer
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.messaging import (
    OutgoingMessage,
    Recipient,
    WorkflowActionTriggerPayload,
    WorkflowMessage,
)
from roster_agent_runtime.singletons import (
    get_agent_pool,
    get_rabbitmq,
    get_roster_informer,
)

from .rabbitmq import RabbitMQClient

logger = app_logger()


def queue_name_for_recipient(recipient: Recipient) -> str:
    return f"{recipient.namespace}:actor:{recipient.kind}:{recipient.name}"


def queue_name_for_agent(agent_name: str, namespace: str = "default") -> str:
    return f"{namespace}:actor:agent:{agent_name}"


class AgentMessageRouter:
    def __init__(
        self,
        agent_handle: AgentHandle,
        queue_name: str,
        rmq_client: Optional[RabbitMQClient] = None,
    ):
        self.agent_handle = agent_handle
        self.queue_name = queue_name
        self.rmq_client = rmq_client or get_rabbitmq()
        self.outbox_consumer: Optional[asyncio.Task] = None

    async def setup(self):
        # Register callback for incoming messages
        await self.rmq_client.register_callback(
            self.queue_name, self.handle_incoming_message
        )
        # Set up consuming task for outgoing messages
        self.outbox_consumer = asyncio.create_task(self.consume_outgoing_messages())

    async def teardown(self):
        await self.rmq_client.deregister_callback(
            self.queue_name, self.handle_incoming_message
        )
        self.outbox_consumer.cancel()
        self.outbox_consumer = None

    async def handle_incoming_message(self, message: str):
        try:
            message_data = json.loads(message)
            workflow_message = WorkflowMessage(**message_data)
            action_trigger = WorkflowActionTriggerPayload(**workflow_message.data)
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.debug(
                "(agent-router) Failed to parse incoming message as action trigger: %s",
                message,
            )
            return

        logger.debug("(agent-router) Received action trigger: %s", action_trigger)
        try:
            await self.agent_handle.trigger_action(
                action=action_trigger.action,
                inputs=action_trigger.inputs,
                record_id=workflow_message.id,
                workflow=workflow_message.workflow,
            )
        except Exception as e:
            logger.debug("(agent-router) Failed to trigger action: %s", e)

    async def consume_outgoing_messages(self):
        # TODO: resiliency if the stream is broken
        async for message in self.agent_handle.outgoing_message_stream():
            await self.send_outgoing_message(message=message)

    async def send_outgoing_message(self, message: OutgoingMessage):
        await self.rmq_client.publish_json(
            queue_name=queue_name_for_recipient(message.recipient),
            message=message.payload,
        )


class MessageRouter:
    def __init__(
        self,
        agent_pool: Optional[AgentPool] = None,
        roster_informer: Optional[RosterInformer] = None,
        rmq_client: Optional[RabbitMQClient] = None,
    ):
        self.agent_pool = agent_pool or get_agent_pool()
        self.roster_informer = roster_informer or get_roster_informer()
        self.rmq_client = rmq_client or get_rabbitmq()
        self.agent_routers: dict[str, AgentMessageRouter] = {}

    async def setup(self):
        await self._setup_initial_agent_routers()
        self.roster_informer.add_event_listener(self.handle_agent_change)

    async def _setup_initial_agent_routers(self):
        agents = self.roster_informer.list()
        setup_coros = []
        for agent in agents:
            handle = self.agent_pool.get_agent_handle(agent.name)
            agent_router = AgentMessageRouter(
                agent_handle=handle,
                queue_name=queue_name_for_agent(agent.name),
                rmq_client=self.rmq_client,
            )
            self.agent_routers[agent.name] = agent_router
            setup_coros.append(agent_router.setup())
        await asyncio.gather(*setup_coros)

    async def teardown(self):
        teardown_coros = []
        for agent_router in self.agent_routers.values():
            teardown_coros.append(agent_router.teardown())
        await asyncio.gather(*teardown_coros)
        self.agent_routers = {}

    def handle_agent_change(self, event: RosterResourceEvent):
        logger.info("Router received spec event: %s", event)
        if event.resource_type != "AGENT":
            logger.debug("(agent-router) Unknown event: %s", event)
            return

        # TODO: handle race conditions due to Task creation here
        if event.event_type == "PUT":
            asyncio.create_task(self._handle_agent_added(event))
        elif event.event_type == "DELETE":
            asyncio.create_task(self._handle_agent_removed(event))
        else:
            logger.debug("(agent-router) Unknown event: %s", event)

    async def _handle_agent_added(self, event: RosterResourceEvent):
        if event.name in self.agent_routers:
            logger.debug(
                "(agent-router) Router already exists for %s, ignoring", event.name
            )
            return

        handle = self.agent_pool.get_agent_handle(event.name)
        agent_router = AgentMessageRouter(
            agent_handle=handle,
            queue_name=queue_name_for_agent(event.name),
            rmq_client=self.rmq_client,
        )
        self.agent_routers[event.name] = agent_router
        await agent_router.setup()

    async def _handle_agent_removed(self, event: RosterResourceEvent):
        agent_router = self.agent_routers.pop(event.name, None)
        if agent_router is None:
            logger.debug(
                "(agent-router) Agent (%s) removed but router not found, ignoring",
                event.name,
            )
            return

        await agent_router.teardown()

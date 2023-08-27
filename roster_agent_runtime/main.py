import asyncio
from typing import Optional

from fastapi import FastAPI
from uvicorn import Config, Server

from roster_agent_runtime import constants, errors, settings
from roster_agent_runtime.api.messaging import router as messaging_router
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.singletons import (
    get_agent_controller,
    get_agent_executor,
    get_message_router,
    get_rabbitmq,
    get_roster_informer,
    get_roster_notifier,
)

logger = app_logger()

app = FastAPI(title="Roster Runtime API", version="0.1.0")
controller = get_agent_controller()
informer = get_roster_informer()
notifier = get_roster_notifier()
executor = get_agent_executor()
rmq_client = get_rabbitmq()
message_router = get_message_router()

CONTROLLER_TASK: Optional[asyncio.Task] = None


# TODO: Dependency injection or context managers might be better pattern for setup/teardown
#   - could solve issues like triggering clean teardown while setup in-progress


@app.on_event("startup")
async def startup_event():
    # Notifier setup is synchronous, manages asyncio Task internally
    # TODO: unnecessary complexity for questionable performance reasons, probably no need
    notifier.setup()
    # Set up lower-level components
    await asyncio.gather(informer.setup(), executor.setup(), rmq_client.setup())
    # Set up higher-level components
    await asyncio.gather(controller.setup(), message_router.setup())
    # Start core Controller loop
    global CONTROLLER_TASK
    CONTROLLER_TASK = asyncio.create_task(controller.run())


@app.on_event("shutdown")
async def shutdown_event():
    if CONTROLLER_TASK:
        CONTROLLER_TASK.cancel()
        await CONTROLLER_TASK
    try:
        # teardown in reverse of setup
        await asyncio.gather(controller.teardown(), message_router.teardown())
        await asyncio.gather(
            informer.teardown(), executor.teardown(), rmq_client.teardown()
        )
        notifier.teardown()
    except errors.TeardownError as e:
        logger.error(f"(shutdown_event): {e}")


async def serve_api():
    app.include_router(messaging_router, prefix=f"/{constants.API_VERSION}")
    config = Config(app=app, host="0.0.0.0", port=settings.PORT)
    server = Server(config)
    await server.serve()


async def main():
    loop = asyncio.get_event_loop()
    loop.set_debug(settings.DEBUG)

    await serve_api()


def run():
    try:
        asyncio.run(main())
    except asyncio.CancelledError:
        pass

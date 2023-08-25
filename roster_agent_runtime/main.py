import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from uvicorn import Config, Server

from roster_agent_runtime import constants, settings
from roster_agent_runtime.api.messaging import router as messaging_router
from roster_agent_runtime.singletons import get_agent_controller, get_rabbitmq

app = FastAPI(title="Roster Runtime API", version="0.1.0")
controller = get_agent_controller()
rmq_client = get_rabbitmq()

CONTROLLER_TASK: Optional[asyncio.Task] = None


@app.on_event("startup")
async def startup_event():
    await controller.setup()
    await rmq_client.setup()
    CONTROLLER_TASK = asyncio.create_task(controller.run())


@app.on_event("shutdown")
async def shutdown_event():
    if CONTROLLER_TASK:
        CONTROLLER_TASK.cancel()
        await CONTROLLER_TASK
    await controller.teardown()
    await rmq_client.teardown()


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

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from uvicorn import Config, Server

from roster_agent_runtime import constants, settings
from roster_agent_runtime.api.messaging import router as messaging_router
from roster_agent_runtime.singletons import get_agent_controller


# Running the API Server and Controller in the same process
# isn't great, and it means uvicorn needs to cancel tasks
# when it receives a shutdown signal.
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        print("Runtime API received shutdown signal, cancelling tasks...")
        for task in TASKS:
            task.cancel()


async def serve_api():
    app = FastAPI(title="Roster Runtime API", version="0.1.0", lifespan=lifespan)
    app.include_router(messaging_router, prefix=f"/{constants.API_VERSION}/messaging")
    config = Config(app=app, host="0.0.0.0", port=settings.PORT)
    server = Server(config)
    await server.serve()


async def run_controller():
    controller = get_agent_controller()
    await controller.setup()
    try:
        await controller.run()
    finally:
        await controller.teardown()


COMPONENTS = [serve_api, run_controller]
TASKS = []


async def main():
    loop = asyncio.get_event_loop()
    loop.set_debug(settings.DEBUG)

    global TASKS
    TASKS = [asyncio.create_task(component()) for component in COMPONENTS]

    await asyncio.gather(*TASKS)


def run():
    try:
        asyncio.run(main())
    except asyncio.CancelledError:
        pass

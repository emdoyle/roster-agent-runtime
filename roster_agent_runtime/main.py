import uvicorn
from fastapi import FastAPI

from roster_agent_runtime import settings
from roster_agent_runtime.api.agent import router as agent_router
from roster_agent_runtime.api.messaging import router as messaging_router


def create_app() -> FastAPI:
    app = FastAPI(title="Roster Agent Runtime", version="0.1.0")
    app.include_router(agent_router)
    app.include_router(messaging_router)
    return app


def run():
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)


if __name__ == "__main__":
    run()

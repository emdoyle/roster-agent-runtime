from fastapi import APIRouter, HTTPException
from roster_agent_runtime import errors
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.api.messaging import ChatPromptAgentArgs
from roster_agent_runtime.singletons import get_agent_service

router = APIRouter()

logger = app_logger()


@router.post("/agent/{name}/chat", tags=["AgentResource", "Messaging"])
async def chat_prompt_agent(name: str, prompt: ChatPromptAgentArgs):
    try:
        return await get_agent_service().chat_prompt_agent(
            name, prompt.history, prompt.message, team=prompt.team
        )
    except errors.AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)

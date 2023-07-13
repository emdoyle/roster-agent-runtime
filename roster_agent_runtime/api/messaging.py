from fastapi import APIRouter, HTTPException, Request
from roster_agent_runtime import errors
from roster_agent_runtime.constants import EXECUTION_ID_HEADER, EXECUTION_TYPE_HEADER
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.api.messaging import ChatPromptAgentArgs
from roster_agent_runtime.singletons import get_agent_service

router = APIRouter()

logger = app_logger()


@router.post("/agent/{name}/chat", tags=["AgentResource", "Messaging"])
async def chat_prompt_agent(
    request: Request, name: str, prompt: ChatPromptAgentArgs
) -> str:
    execution_id = request.headers.get(EXECUTION_ID_HEADER, "")
    execution_type = request.headers.get(EXECUTION_TYPE_HEADER, "")

    try:
        return await get_agent_service().chat_prompt_agent(
            name=name,
            identity=prompt.identity,
            team=prompt.team,
            role=prompt.role,
            history=prompt.history,
            message=prompt.message,
            execution_id=execution_id,
            execution_type=execution_type,
        )
    except errors.AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)

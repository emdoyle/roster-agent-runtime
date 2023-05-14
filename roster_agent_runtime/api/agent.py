from fastapi import APIRouter, Depends, responses, status
from roster_agent_runtime.api.routes import create_error_handling_route
from roster_agent_runtime.models.agent import AgentResource
from roster_agent_runtime.models.conversation import (
    ConversationMessage,
    ConversationResource,
)
from roster_agent_runtime.models.task import TaskResource
from roster_agent_runtime.services.agent import AgentService, get_agent_service
from roster_agent_runtime.services.agent.errors import (
    AgentImageNotFoundError,
    AgentNotFoundError,
    AgentServiceError,
    ConversationAlreadyExistsError,
    ConversationNotFoundError,
)

route = create_error_handling_route()
router = APIRouter(route_class=route)


@router.post(
    "/agent", response_model=AgentResource, status_code=status.HTTP_201_CREATED
)
async def create_agent(
    agent: AgentResource, agent_service: AgentService = Depends(get_agent_service)
):
    return await agent_service.create_agent(agent)


@router.get("/agent", response_model=list[AgentResource])
async def list_agents(agent_service: AgentService = Depends(get_agent_service)):
    return await agent_service.list_agents()


@router.get("/agent/{name}", response_model=AgentResource)
async def get_agent(
    name: str, agent_service: AgentService = Depends(get_agent_service)
):
    return await agent_service.get_agent(name)


@router.delete("/agent/{name}", response_model=AgentResource)
async def delete_agent(
    name: str, agent_service: AgentService = Depends(get_agent_service)
):
    return await agent_service.delete_agent(name)


@router.post("/task", response_model=TaskResource)
async def initiate_task(
    task: TaskResource,
    agent_service: AgentService = Depends(get_agent_service),
):
    return await agent_service.initiate_task(task)


@router.post("/conversation", response_model=ConversationResource)
async def start_conversation(
    conversation: ConversationResource,
    agent_service: AgentService = Depends(get_agent_service),
):
    return await agent_service.start_conversation(conversation)


@router.post(
    "/conversation/{conversation_id}/prompt",
    response_model=ConversationResource,
)
async def prompt(
    conversation_id: str,
    conversation_message: ConversationMessage,
    agent_service: AgentService = Depends(get_agent_service),
):
    return await agent_service.prompt(conversation_id, conversation_message)


@router.post(
    "/conversation/{conversation_id}/end",
    response_model=ConversationResource,
)
async def end_conversation(
    conversation_id: str,
    agent_service: AgentService = Depends(get_agent_service),
):
    return await agent_service.end_conversation(conversation_id)


# Exception Handlers


@route.exception_handler(AgentImageNotFoundError)
async def agent_image_not_found_error_handler(request, exc: AgentImageNotFoundError):
    return responses.JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"message": f"Agent image not found: {exc.image}"},
    )


@route.exception_handler(AgentNotFoundError)
async def agent_not_found_error_handler(request, exc: AgentNotFoundError):
    return responses.JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"message": f"Agent not found: {exc.agent}"},
    )


@route.exception_handler(AgentServiceError)
async def agent_service_error_handler(request, exc: AgentServiceError):
    return responses.JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": f"Agent service error: {exc.message}"},
    )


@route.exception_handler(ConversationNotFoundError)
async def conversation_not_found_error_handler(request, exc: ConversationNotFoundError):
    return responses.JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"message": f"Conversation not found: {exc.conversation}"},
    )


@route.exception_handler(ConversationAlreadyExistsError)
async def conversation_already_exists_error_handler(
    request, exc: ConversationAlreadyExistsError
):
    return responses.JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"message": f"Conversation already exists: {exc.conversation}"},
    )

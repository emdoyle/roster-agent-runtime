from fastapi import APIRouter, Depends, responses, status
from roster_agent_runtime.api.routes import create_error_handling_route
from roster_agent_runtime.models.agent import AgentContainer, AgentResource
from roster_agent_runtime.services.agent import AgentService, get_agent_service
from roster_agent_runtime.services.agent.errors import (
    AgentImageNotFoundError,
    AgentNotFoundError,
    AgentServiceError,
)

route = create_error_handling_route()
router = APIRouter(route_class=route)


@router.post("/agent", response_model=AgentContainer)
async def create_agent(
    agent: AgentResource, agent_service: AgentService = Depends(get_agent_service)
):
    return agent_service.create_agent(agent)


@router.get("/agent", response_model=list[AgentContainer])
async def list_agents(agent_service: AgentService = Depends(get_agent_service)):
    return agent_service.list_agents()


@router.get("/agent/{id}", response_model=AgentContainer)
async def get_agent(id: str, agent_service: AgentService = Depends(get_agent_service)):
    return agent_service.get_agent(id)


@router.delete("/agent/{id}", response_model=AgentContainer)
async def delete_agent(
    id: str, agent_service: AgentService = Depends(get_agent_service)
):
    return agent_service.delete_agent(id)


@router.post("/agent/{id}/start")
async def start_agent(
    id: str, agent_service: AgentService = Depends(get_agent_service)
):
    return agent_service.start_agent(id)


@router.post("/agent/{id}/stop")
async def stop_agent(id: str, agent_service: AgentService = Depends(get_agent_service)):
    return agent_service.stop_agent(id)


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

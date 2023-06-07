from fastapi import APIRouter, HTTPException
from roster_agent_runtime import errors
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.singletons import get_agent_service

router = APIRouter()

logger = app_logger()


@router.post("/agent/{name}/tasks", tags=["AgentResource", "Tasks"])
async def initiate_task_on_agent(name: str, task: str, description: str):
    try:
        return await get_agent_service().initiate_task_on_agent(name, task, description)
    except errors.AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.get("/agent/{name}/tasks", tags=["AgentResource", "Tasks"])
async def list_tasks_on_agent(name: str):
    try:
        return await get_agent_service().list_tasks_on_agent(name)
    except errors.AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.get("/agent/{name}/tasks/{task}", tags=["AgentResource", "Tasks"])
async def get_task_on_agent(name: str, task: str):
    try:
        return await get_agent_service().get_task_on_agent(name, task)
    except errors.AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.delete("/agent/{name}/tasks/{task}", tags=["AgentResource", "Tasks"])
async def cancel_task_on_agent(name: str, task: str):
    try:
        return await get_agent_service().cancel_task_on_agent(name, task)
    except errors.AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)

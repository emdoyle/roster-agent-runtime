from typing import Optional

from pydantic import BaseModel, Field

from .agent import AgentContainer


class TaskResource(BaseModel):
    agent_name: str = Field(description="The name of the agent.")
    name: str = Field(description="The name of the task.")
    description: str = Field(description="The description of the task.")
    id: str = Field(description="The id of the task.")
    status: str = Field(description="The status of the task.")
    container: Optional[AgentContainer] = Field(
        default=None,
        description="The running container of the agent executing the task.",
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "agent_name": "Alice",
                "name": "my_task",
                "description": "my task",
                "id": "my_task_id",
                "status": "running",
                "container": AgentContainer.Config.schema_extra["example"],
            }
        }

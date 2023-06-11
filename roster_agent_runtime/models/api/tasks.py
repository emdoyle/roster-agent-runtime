from typing import Optional

from pydantic import BaseModel, Field

from ..task import TaskAssignment


class InitiateTaskArgs(BaseModel):
    task: str = Field(description="The name of the task.")
    description: str = Field(description="The description of the task.")
    assignment: Optional[TaskAssignment] = Field(
        default=None, description="Who is assigned to the task."
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "task": "my_task",
                "description": "my task",
                "assignment": TaskAssignment.Config.schema_extra["example"],
            }
        }

from pydantic import BaseModel, Field


class TaskSpec(BaseModel):
    agent_name: str = Field(description="The name of the agent.")
    name: str = Field(description="The name of the task.")
    description: str = Field(description="The description of the task.")

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "agent_name": "Alice",
                "name": "my_task",
                "description": "my task",
            }
        }


class TaskStatus(BaseModel):
    name: str = Field(description="The name of the task.")
    agent_name: str = Field(description="The name of the agent running the task.")
    status: str = Field(description="The status of the task.")

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "name": "my_task",
                "agent_name": "Alice",
                "status": "running",
            }
        }

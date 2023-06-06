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

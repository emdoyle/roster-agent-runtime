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
    status: str = Field(description="The status of the task.")

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "name": "my_task",
                "status": "running",
            }
        }


class TaskResource(BaseModel):
    spec: TaskSpec = Field(description="The specification of the task.")
    status: TaskStatus = Field(description="The status of the task.")

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "spec": TaskSpec.Config.schema_extra["example"],
                "status": TaskStatus.Config.schema_extra["example"],
            }
        }

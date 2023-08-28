from typing import Optional

from pydantic import BaseModel, Field
from roster_agent_runtime.models.common import TypedArgument


class Action(BaseModel):
    name: str = Field(description="A name to identify the action.")
    description: str = Field(description="A description of the action.")
    inputs: list[TypedArgument] = Field(
        default_factory=list, description="The inputs to the action."
    )
    outputs: list[TypedArgument] = Field(
        default_factory=list, description="The outputs of the action."
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "name": "ActionName",
                "description": "A description of the action.",
                "inputs": [
                    TypedArgument.Config.schema_extra["example"],
                    TypedArgument.Config.schema_extra["example"],
                ],
                "outputs": [
                    TypedArgument.Config.schema_extra["example"],
                    TypedArgument.Config.schema_extra["example"],
                ],
            }
        }


class AgentSpec(BaseModel):
    name: str = Field(description="A name to identify the agent.")
    executor: str = Field(description="The executor which should run the agent.")
    image: str = Field(description="A path to the image to be used for this agent.")
    tag: str = Field(
        description="A tag to identify the version of the image to be used for this agent.",
        default="latest",
    )
    actions: list[Action] = Field(
        default_factory=list, description="The actions implemented by this agent."
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "name": "Alice",
                "executor": "local",
                "image": ".local/agent",
                "tag": "latest",
                "actions": [
                    Action.Config.schema_extra["example"],
                    Action.Config.schema_extra["example"],
                ],
            }
        }


class AgentContainer(BaseModel):
    id: str = Field(description="The id of the container.")
    name: str = Field(
        max_length=128,
        regex=r"^/?[a-zA-Z0-9][a-zA-Z0-9_.-]+$",
        description="The name of the container.",
    )
    image: str = Field(description="The container image.")
    status: str = Field(description="The status of the container")
    labels: Optional[dict[str, str]] = Field(
        default=None, description="The labels of the container."
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "id": "my_container_id",
                "image": "my_image:latest",
                "name": "my_container_name",
                "status": "running",
                "labels": {"my_label": "my_value"},
            }
        }


class AgentStatus(BaseModel):
    name: str = Field(description="The name of the agent.")
    executor: str = Field(description="The executor which is managing the agent.")
    status: str = Field(description="The status of the agent.")
    container: Optional[AgentContainer] = Field(
        default=None, description="The container running the agent."
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "name": "Alice",
                "executor": "local",
                "status": "running",
                "container": AgentContainer.Config.schema_extra["example"],
            }
        }


class AgentResource(BaseModel):
    spec: AgentSpec = Field(description="The specification of the agent.")
    status: AgentStatus = Field(description="The status of the agent.")

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "spec": AgentSpec.Config.schema_extra["example"],
                "status": AgentStatus.Config.schema_extra["example"],
            }
        }

from typing import Optional

from pydantic import BaseModel, Field


class AgentCapabilities(BaseModel):
    network_access: bool = Field(
        False, description="Whether the agent has network access or not."
    )
    messaging_access: bool = Field(
        False, description="Whether the agent can message other agents or not."
    )


class AgentResource(BaseModel):
    image: str = Field(description="The container image to be used for this agent.")
    name: str = Field(description="A name to identify the agent.")
    capabilities: AgentCapabilities = Field(
        default_factory=lambda: AgentCapabilities(),
        description="The capabilities of the agent.",
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "image": "my_image:latest",
                "name": "Alice",
                "capabilities": {
                    "network_access": False,
                    "messaging_access": False,
                },
            }
        }


class AgentContainer(BaseModel):
    id: str = Field(description="The id of the container.")
    image: str = Field(description="The container image.")
    name: str = Field(
        max_length=128,
        regex=r"^/?[a-zA-Z0-9][a-zA-Z0-9_.-]+$",
        description="The container name.",
    )
    agent_name: str = Field(description="The name of the agent.")
    status: str = Field(description="The status of the container.")
    labels: Optional[dict[str, str]] = Field(
        default=None, description="The labels of the container."
    )
    capabilities: AgentCapabilities = Field(
        description="The capabilities of the agent running in the container."
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "id": "my_container_id",
                "image": "my_image:latest",
                "name": "Alice",
                "status": "running",
                "capabilities": {
                    "network_access": False,
                    "messaging_access": False,
                },
            }
        }

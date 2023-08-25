import json
from typing import Literal, Union

from pydantic import BaseModel, Field
from roster_agent_runtime import errors
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.agent import AgentSpec

logger = app_logger()

# TODO: add workflow, maybe team etc.
RosterSpec = Union[AgentSpec]


class Resource(BaseModel):
    # This is the only field we care about for now
    spec: RosterSpec = Field(description="The specification of the resource.")

    class Config:
        validate_assignment = True


class PutResourceEvent(BaseModel):
    event_type: Literal["PUT"] = Field(default="PUT", description="The type of event.")
    resource_type: str = Field(description="The type of resource.")
    namespace: str = Field(
        default="default", description="The namespace of the resource."
    )
    name: str = Field(description="The name of the resource.")
    resource: Resource = Field(description="The resource itself.")

    class Config:
        validate_assignment = True

    def __str__(self):
        return f"({self.event_type} {self.resource_type} {self.namespace}/{self.name})"


class DeleteResourceEvent(BaseModel):
    event_type: Literal["DELETE"] = Field(
        default="DELETE", description="The type of event."
    )
    resource_type: str = Field(description="The type of resource.")
    namespace: str = Field(
        default="default", description="The namespace of the resource."
    )
    name: str = Field(description="The name of the resource.")

    class Config:
        validate_assignment = True

    def __str__(self):
        return f"({self.event_type} {self.resource_type} {self.namespace}/{self.name})"


RosterResourceEvent = Union[PutResourceEvent, DeleteResourceEvent]


def deserialize_resource_event(event: str) -> RosterResourceEvent:
    try:
        json_event = json.loads(json.loads(event))
        logger.debug("Deserialized Resource Event %s", json_event)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise errors.InvalidEventError(f"Invalid Resource Event {event}") from e
    try:
        if json_event["event_type"] == "PUT":
            if json_event["resource_type"] == "AGENT":
                json_event["resource"]["spec"] = AgentSpec(
                    **json_event["resource"]["spec"]
                )
            else:
                raise errors.InvalidEventError(
                    f"Invalid Resource Event (resource_type) {event}"
                )
            return PutResourceEvent(**json_event)
        elif json_event["event_type"] == "DELETE":
            return DeleteResourceEvent(**json_event)
    except Exception as e:
        logger.error("Error deserializing Resource Event %s", e)
    raise errors.InvalidEventError(f"Invalid Resource Event (event_type) {event}")

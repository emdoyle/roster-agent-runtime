import json
from typing import Literal, Union

from pydantic import BaseModel, Field
from roster_agent_runtime import errors
from roster_agent_runtime.models.agent import AgentSpec
from roster_agent_runtime.models.conversation import ConversationSpec
from roster_agent_runtime.models.task import TaskSpec

RosterSpec = Union[AgentSpec, TaskSpec, ConversationSpec]


class PutSpecEvent(BaseModel):
    event_type: Literal["PUT"] = Field(default="PUT", description="The type of event.")
    resource_type: str = Field(description="The type of resource.")
    namespace: str = Field(description="The namespace of the resource.")
    name: str = Field(description="The name of the resource.")
    spec: RosterSpec = Field(description="The specification of the resource.")

    class Config:
        validate_assignment = True

    def __str__(self):
        return f"({self.event_type} {self.resource_type} {self.namespace}/{self.name})"


class DeleteSpecEvent(BaseModel):
    event_type: Literal["DELETE"] = Field(
        default="DELETE", description="The type of event."
    )
    resource_type: str = Field(description="The type of resource.")
    namespace: str = Field(description="The namespace of the agent.")
    name: str = Field(description="The name of the agent.")

    class Config:
        validate_assignment = True

    def __str__(self):
        return f"({self.event_type} {self.resource_type} {self.namespace}/{self.name})"


RosterSpecEvent = Union[PutSpecEvent, DeleteSpecEvent]


def deserialize_spec_event(event: bytes) -> RosterSpecEvent:
    try:
        json_event = json.loads(event.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise errors.InvalidEventError(f"Invalid Spec Event {event}") from e
    if json_event["event_type"] == "PUT":
        if json_event["resource_type"] == "AGENT":
            json_event["spec"] = AgentSpec(**json_event["spec"])
        elif json_event["resource_type"] == "TASK":
            json_event["spec"] = TaskSpec(**json_event["spec"])
        elif json_event["resource_type"] == "CONVERSATION":
            json_event["spec"] = ConversationSpec(**json_event["spec"])
        else:
            raise errors.InvalidEventError(
                f"Invalid Spec Event (resource_type) {event}"
            )
        return PutSpecEvent(**json_event)
    elif json_event["event_type"] == "DELETE":
        return DeleteSpecEvent(**json_event)
    raise errors.InvalidEventError(f"Invalid Spec Event (event_type) {event}")

from enum import Enum
from typing import Optional

from pydantic import BaseModel
from roster_agent_runtime.models.agent import AgentStatus


class Resource(Enum):
    AGENT = "AGENT"


class EventType(Enum):
    PUT = "PUT"
    DELETE = "DELETE"


# TODO: there is no need for a distinct type here, should reconcile w/ ResourceStatusEvent
class ControllerStatusEvent(BaseModel):
    resource_type: Resource
    event_type: EventType
    name: str
    status: Optional[dict] = None

    class Config:
        use_enum_values = True

    def get_agent_status(self) -> AgentStatus:
        try:
            if self.resource_type == Resource.AGENT and self.status is not None:
                return AgentStatus(**self.status)
        except TypeError:
            raise ValueError("Invalid resource_type or data type for agent status")
        raise ValueError("Invalid resource_type or data type for agent status")

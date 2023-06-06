from enum import Enum
from typing import Optional

from pydantic import BaseModel
from roster_agent_runtime.models.agent import AgentStatus


class Resource(Enum):
    AGENT = "Agent"


class EventType(Enum):
    PUT = "Put"
    DELETE = "Delete"


class ExecutorStatusEvent(BaseModel):
    resource_type: Resource
    event_type: EventType
    name: str
    data: Optional[BaseModel] = None

    def get_agent_status(self) -> AgentStatus:
        if self.resource_type == Resource.AGENT and isinstance(self.data, AgentStatus):
            return self.data
        raise ValueError("Invalid resource_type or data type for agent status")

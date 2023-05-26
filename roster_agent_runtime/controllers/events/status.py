from enum import Enum
from typing import Optional

from pydantic import BaseModel
from roster_agent_runtime.models.agent import AgentStatus
from roster_agent_runtime.models.task import TaskStatus


class Resource(Enum):
    AGENT = "AGENT"
    TASK = "TASK"


class EventType(Enum):
    PUT = "PUT"
    DELETE = "DELETE"


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

    def get_task_status(self) -> TaskStatus:
        try:
            if self.resource_type == Resource.TASK and self.status is not None:
                return TaskStatus(**self.status)
        except TypeError:
            raise ValueError("Invalid resource_type or data type for task status")
        raise ValueError("Invalid resource_type or data type for task status")

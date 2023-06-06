from typing import Callable, Optional

from roster_agent_runtime import errors
from roster_agent_runtime.controllers.events.status import (
    ControllerStatusEvent,
    EventType,
    Resource,
)
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.agent import AgentStatus
from roster_agent_runtime.models.controller import CurrentAgentState, DesiredAgentState

logger = app_logger()


class AgentControllerStore:
    def __init__(
        self,
        status_listeners: Optional[
            list[Callable[[ControllerStatusEvent], None]]
        ] = None,
    ):
        self.desired = DesiredAgentState()
        self.current = CurrentAgentState()
        self.status_listeners = status_listeners or []

    def add_status_listener(self, listener: Callable[[ControllerStatusEvent], None]):
        self.status_listeners.append(listener)

    def remove_status_listener(self, listener: Callable[[ControllerStatusEvent], None]):
        self.status_listeners.remove(listener)

    def _notify_status_listeners(self, event: ControllerStatusEvent):
        for listener in self.status_listeners:
            listener(event)

    def put_agent(self, agent_name: str, agent_status: AgentStatus):
        logger.debug("(store) put agent: %s", agent_name)
        self.current.agents[agent_name] = agent_status
        self._notify_status_listeners(
            ControllerStatusEvent(
                resource_type=Resource.AGENT,
                event_type=EventType.PUT,
                name=agent_name,
                status=agent_status.dict(),
            )
        )

    def delete_agent(self, agent_name: str):
        logger.debug("(store) delete agent: %s", agent_name)
        try:
            self.current.agents.pop(agent_name)
            self._notify_status_listeners(
                ControllerStatusEvent(
                    resource_type=Resource.AGENT,
                    event_type=EventType.DELETE,
                    name=agent_name,
                )
            )
        except KeyError:
            raise errors.AgentNotFoundError(agent_name)

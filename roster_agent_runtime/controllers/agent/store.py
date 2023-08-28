from typing import Callable, Optional

from roster_agent_runtime import errors
from roster_agent_runtime.controllers.events.status import (
    ControllerStatusEvent,
    EventType,
    Resource,
)
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.agent import AgentSpec, AgentStatus

logger = app_logger()


class AgentControllerStore:
    def __init__(
        self,
        status_listeners: Optional[
            list[Callable[[ControllerStatusEvent], None]]
        ] = None,
    ):
        self.desired: dict[str, AgentSpec] = {}
        self.current: dict[str, AgentStatus] = {}
        self.status_listeners = status_listeners or []

    def add_status_listener(self, listener: Callable[[ControllerStatusEvent], None]):
        self.status_listeners.append(listener)

    def remove_status_listener(self, listener: Callable[[ControllerStatusEvent], None]):
        self.status_listeners.remove(listener)

    def _notify_status_listeners(self, event: ControllerStatusEvent):
        for listener in self.status_listeners:
            try:
                listener(event)
            except Exception as e:
                logger.debug(
                    "(agent-ctrl-store) error notifying status listener: %s; %s",
                    listener,
                    e,
                )

    def put_agent_spec(self, agent_spec: AgentSpec):
        logger.debug("(agent-ctrl-store) put agent spec: %s", agent_spec.name)
        self.desired[agent_spec.name] = agent_spec

    def delete_agent_spec(self, agent_name: str):
        logger.debug("(agent-ctrl-store) delete agent spec: %s", agent_name)
        try:
            self.desired.pop(agent_name)
        except KeyError:
            raise errors.AgentNotFoundError(agent_name)

    def put_agent_status(self, agent_status: AgentStatus):
        logger.debug("(agent-ctrl-store) put agent status: %s", agent_status.name)
        self.current[agent_status.name] = agent_status
        self._notify_status_listeners(
            ControllerStatusEvent(
                resource_type=Resource.AGENT,
                event_type=EventType.PUT,
                name=agent_status.name,
                status=agent_status.dict(),
            )
        )

    def delete_agent_status(self, agent_name: str):
        logger.debug("(agent-ctrl-store) delete agent status: %s", agent_name)
        try:
            self.current.pop(agent_name)
            self._notify_status_listeners(
                ControllerStatusEvent(
                    resource_type=Resource.AGENT,
                    event_type=EventType.DELETE,
                    name=agent_name,
                )
            )
        except KeyError:
            raise errors.AgentNotFoundError(agent_name)

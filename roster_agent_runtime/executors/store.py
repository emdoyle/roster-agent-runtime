from typing import Callable, Optional

from roster_agent_runtime import errors
from roster_agent_runtime.executors.events import (
    EventType,
    ExecutorStatusEvent,
    Resource,
)
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.agent import AgentStatus

logger = app_logger()


class AgentExecutorStore:
    def __init__(
        self,
        status_listeners: Optional[list[Callable[[ExecutorStatusEvent], None]]] = None,
    ):
        self.agents: dict[str, AgentStatus] = {}
        self.status_listeners = status_listeners or []

    def add_status_listener(self, listener: Callable[[ExecutorStatusEvent], None]):
        self.status_listeners.append(listener)

    def remove_status_listener(self, listener: Callable[[ExecutorStatusEvent], None]):
        self.status_listeners.remove(listener)

    def _notify_status_listeners(self, event: ExecutorStatusEvent):
        for listener in self.status_listeners:
            listener(event)

    def put_agent(self, agent: AgentStatus, notify: bool = False):
        agent_name = agent.name
        logger.debug("(exec-store) put agent: %s", agent_name)
        self.agents[agent_name] = agent
        if notify:
            self._notify_status_listeners(
                ExecutorStatusEvent(
                    resource_type=Resource.AGENT,
                    event_type=EventType.PUT,
                    name=agent_name,
                    data=agent,
                )
            )

    def delete_agent(self, agent_name: str, notify: bool = False):
        logger.debug("(exec-store) delete agent: %s", agent_name)
        try:
            self.agents.pop(agent_name)
            if notify:
                self._notify_status_listeners(
                    ExecutorStatusEvent(
                        resource_type=Resource.AGENT,
                        event_type=EventType.DELETE,
                        name=agent_name,
                    )
                )
        except KeyError:
            raise errors.AgentNotFoundError(agent_name)

    def reset(self):
        logger.debug("(exec-store) reset")
        self.agents = {}

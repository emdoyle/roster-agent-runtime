from typing import Callable, Optional

from pydantic import BaseModel
from roster_agent_runtime import errors
from roster_agent_runtime.executors.events import (
    EventType,
    ExecutorStatusEvent,
    Resource,
)
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.agent import AgentStatus
from roster_agent_runtime.models.task import TaskStatus

logger = app_logger()


class RunningAgent(BaseModel):
    status: AgentStatus
    tasks: dict[str, TaskStatus] = {}


class AgentExecutorStore:
    def __init__(
        self,
        status_listeners: Optional[list[Callable[[ExecutorStatusEvent], None]]] = None,
    ):
        self.agents: dict[str, RunningAgent] = {}
        self.tasks: dict[str, TaskStatus] = {}
        self.status_listeners = status_listeners or []

    def add_status_listener(self, listener: Callable[[ExecutorStatusEvent], None]):
        self.status_listeners.append(listener)

    def remove_status_listener(self, listener: Callable[[ExecutorStatusEvent], None]):
        self.status_listeners.remove(listener)

    def _notify_status_listeners(self, event: ExecutorStatusEvent):
        for listener in self.status_listeners:
            listener(event)

    def put_agent(self, running_agent: RunningAgent, notify: bool = False):
        agent_name = running_agent.status.name
        logger.debug("(exec-store) put agent: %s", agent_name)
        self.agents[agent_name] = running_agent
        if notify:
            self._notify_status_listeners(
                ExecutorStatusEvent(
                    resource_type=Resource.AGENT,
                    event_type=EventType.PUT,
                    name=agent_name,
                    data=running_agent,
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

    def put_task(self, task_status: TaskStatus, notify: bool = False):
        task_name = task_status.name
        logger.debug("(exec-store) put task: %s", task_name)
        try:
            self.tasks[task_name] = task_status
            self.agents[task_status.agent_name].tasks[task_name] = task_status
            if notify:
                self._notify_status_listeners(
                    ExecutorStatusEvent(
                        resource_type=Resource.TASK,
                        event_type=EventType.PUT,
                        name=task_name,
                        data=task_status,
                    )
                )
        except KeyError:
            raise errors.AgentNotFoundError(task_status.agent_name)

    def delete_task(self, task_name: str, notify: bool = False):
        logger.debug("(exec-store) delete task: %s", task_name)
        try:
            self.tasks.pop(task_name)
            if notify:
                self._notify_status_listeners(
                    ExecutorStatusEvent(
                        resource_type=Resource.TASK,
                        event_type=EventType.DELETE,
                        name=task_name,
                    )
                )
        except KeyError:
            raise errors.TaskNotFoundError(task_name)

    def reset(self):
        logger.debug("(exec-store) reset")
        self.agents = {}
        self.tasks = {}

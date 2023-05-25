from abc import ABC, abstractmethod
from typing import Callable

from roster_agent_runtime.executors.events import ExecutorStatusEvent
from roster_agent_runtime.models.agent import AgentSpec, AgentStatus
from roster_agent_runtime.models.conversation import ConversationMessage
from roster_agent_runtime.models.task import TaskSpec, TaskStatus


class AgentExecutor(ABC):
    @abstractmethod
    async def setup(self):
        """setup executor -- called once on startup to load status from environment"""

    @abstractmethod
    async def teardown(self):
        """teardown executor -- called once on shutdown to clean up resources"""

    @abstractmethod
    def list_agents(self) -> list[AgentStatus]:
        """list agents"""

    @abstractmethod
    def get_agent(self, name: str) -> AgentStatus:
        """get agent"""

    @abstractmethod
    async def create_agent(self, agent: AgentSpec) -> AgentStatus:
        """create agent"""

    @abstractmethod
    async def update_agent(self, agent: AgentSpec) -> AgentStatus:
        """update agent"""

    @abstractmethod
    async def delete_agent(self, name: str) -> None:
        """delete agent"""

    @abstractmethod
    async def initiate_task(self, task: TaskSpec) -> TaskStatus:
        """start task"""

    @abstractmethod
    async def update_task(self, task: TaskSpec) -> TaskStatus:
        """update task"""

    @abstractmethod
    def list_tasks(self) -> list[TaskStatus]:
        """list tasks"""

    @abstractmethod
    def get_task(self, name: str) -> TaskStatus:
        """get task"""

    @abstractmethod
    async def end_task(self, name: str) -> None:
        """end task"""

    @abstractmethod
    async def prompt(
        self,
        name: str,
        history: list[ConversationMessage],
        message: ConversationMessage,
    ) -> ConversationMessage:
        """prompt agent in conversation"""

    @abstractmethod
    def add_event_listener(self, listener: Callable[[ExecutorStatusEvent], None]):
        """add listener"""

    @abstractmethod
    def remove_event_listener(self, listener: Callable[[ExecutorStatusEvent], None]):
        """remove listener"""

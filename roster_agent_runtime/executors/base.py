from abc import ABC, abstractmethod

from roster_agent_runtime.models.agent import AgentSpec, AgentStatus
from roster_agent_runtime.models.conversation import (
    ConversationMessage,
    ConversationResource,
)
from roster_agent_runtime.models.task import TaskSpec, TaskStatus


class AgentExecutor(ABC):
    @abstractmethod
    async def list_agents(self) -> list[AgentStatus]:
        """list agents"""

    @abstractmethod
    async def get_agent(self, name: str) -> AgentStatus:
        """get agent"""

    @abstractmethod
    async def create_agent(self, agent: AgentSpec) -> AgentStatus:
        """create agent"""

    @abstractmethod
    async def update_agent(self, agent: AgentSpec) -> AgentStatus:
        """update agent"""

    @abstractmethod
    async def prompt(
        self,
        conversation: ConversationResource,
        message: ConversationMessage,
    ) -> ConversationMessage:
        """prompt agent in conversation"""

    @abstractmethod
    async def initiate_task(self, task: TaskSpec) -> TaskStatus:
        """start task on agent"""

    @abstractmethod
    async def delete_agent(self, agent: AgentSpec) -> None:
        """delete agent"""

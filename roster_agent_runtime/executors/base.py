from abc import ABC, abstractmethod

from roster_agent_runtime.models.agent import AgentResource
from roster_agent_runtime.models.conversation import (
    ConversationMessage,
    ConversationResource,
)
from roster_agent_runtime.models.task import TaskResource


class AgentExecutor(ABC):
    @abstractmethod
    async def create_agent(self, agent: AgentResource) -> AgentResource:
        """create agent"""

    @abstractmethod
    async def prompt(
        self,
        conversation: ConversationResource,
        message: ConversationMessage,
    ) -> ConversationResource:
        """prompt agent in conversation"""

    @abstractmethod
    async def initiate_task(self, task: TaskResource) -> TaskResource:
        """start task on agent"""

    @abstractmethod
    async def delete_agent(self, agent: AgentResource) -> AgentResource:
        """delete agent"""

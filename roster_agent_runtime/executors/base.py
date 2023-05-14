from abc import ABC, abstractmethod

from roster_agent_runtime.models.agent import AgentResource
from roster_agent_runtime.models.conversation import (
    ConversationPrompt,
    ConversationResource,
)
from roster_agent_runtime.models.task import TaskResource


class AgentExecutor(ABC):
    @abstractmethod
    def create_agent(self, agent: AgentResource) -> AgentResource:
        """create agent"""

    @abstractmethod
    def prompt(
        self,
        conversation: ConversationResource,
        prompt: ConversationPrompt,
    ) -> ConversationResource:
        """prompt agent in conversation"""

    @abstractmethod
    def initiate_task(self, task: TaskResource) -> TaskResource:
        """start task on agent"""

    @abstractmethod
    def delete_agent(self, agent: AgentResource) -> AgentResource:
        """delete agent"""

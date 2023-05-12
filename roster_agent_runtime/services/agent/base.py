from abc import ABC, abstractmethod
from typing import Optional

from roster_agent_runtime.models.agent import AgentResource
from roster_agent_runtime.models.conversation import (
    ConversationPrompt,
    ConversationResource,
)
from roster_agent_runtime.models.task import TaskResource

AGENT_SERVICE: Optional["AgentService"] = None


def get_agent_service() -> "AgentService":
    global AGENT_SERVICE
    if AGENT_SERVICE is not None:
        return AGENT_SERVICE

    from .docker import DockerAgentService

    AGENT_SERVICE = DockerAgentService()
    return AGENT_SERVICE


class AgentService(ABC):
    @abstractmethod
    def create_agent(self, agent: AgentResource) -> AgentResource:
        """create agent"""

    @abstractmethod
    def list_agents(self) -> list[AgentResource]:
        """list agents"""

    @abstractmethod
    def get_agent(self, name: str) -> AgentResource:
        """get agent by name"""

    @abstractmethod
    def delete_agent(self, name: str) -> AgentResource:
        """delete agent by name"""

    @abstractmethod
    def initiate_task(self, name: str, task: TaskResource) -> TaskResource:
        """start task on agent by name"""

    @abstractmethod
    def start_conversation(
        self, name: str, conversation: ConversationResource
    ) -> ConversationResource:
        """start conversation on agent by name"""

    @abstractmethod
    def prompt(
        self, name: str, conversation_id: str, conversation_prompt: ConversationPrompt
    ) -> ConversationResource:
        """prompt agent by name in conversation"""

    @abstractmethod
    def end_conversation(self, name: str, conversation_id: str) -> ConversationResource:
        """end conversation on agent by name"""

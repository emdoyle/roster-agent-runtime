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

    # These should both be configurable in settings
    from roster_agent_runtime.executors.docker import DockerAgentExecutor

    from .local import LocalAgentService

    AGENT_SERVICE = LocalAgentService(executor=DockerAgentExecutor())
    return AGENT_SERVICE


class AgentService(ABC):
    @abstractmethod
    async def create_agent(self, agent: AgentResource) -> AgentResource:
        """create agent"""

    @abstractmethod
    async def list_agents(self) -> list[AgentResource]:
        """list agents"""

    @abstractmethod
    async def get_agent(self, name: str) -> AgentResource:
        """get agent by name"""

    @abstractmethod
    async def delete_agent(self, name: str) -> AgentResource:
        """delete agent by name"""

    @abstractmethod
    async def initiate_task(self, task: TaskResource) -> TaskResource:
        """start task"""

    @abstractmethod
    async def start_conversation(
        self, conversation: ConversationResource
    ) -> ConversationResource:
        """start conversation"""

    @abstractmethod
    async def prompt(
        self, conversation_id: str, conversation_prompt: ConversationPrompt
    ) -> ConversationResource:
        """prompt agent in conversation"""

    @abstractmethod
    async def end_conversation(self, conversation_id: str) -> ConversationResource:
        """end conversation"""

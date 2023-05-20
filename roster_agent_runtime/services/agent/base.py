from abc import ABC, abstractmethod
from typing import Optional

from roster_agent_runtime.models.agent import AgentSpec, AgentStatus
from roster_agent_runtime.models.conversation import (
    ConversationMessage,
    ConversationSpec,
    ConversationStatus,
)
from roster_agent_runtime.models.task import TaskSpec, TaskStatus

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
    async def create_agent(self, agent: AgentSpec) -> AgentStatus:
        """create agent"""

    @abstractmethod
    async def update_agent(self, agent: AgentSpec) -> AgentStatus:
        """update agent"""

    @abstractmethod
    async def list_agents(self) -> list[AgentStatus]:
        """list agents"""

    @abstractmethod
    async def get_agent(self, name: str) -> AgentStatus:
        """get agent by name"""

    @abstractmethod
    async def delete_agent(self, name: str) -> None:
        """delete agent by name"""

    @abstractmethod
    async def initiate_task(self, task: TaskSpec) -> TaskStatus:
        """start task"""

    @abstractmethod
    async def start_conversation(
        self, conversation: ConversationSpec
    ) -> ConversationStatus:
        """start conversation"""

    @abstractmethod
    async def prompt(
        self, name: str, conversation_message: ConversationMessage
    ) -> ConversationStatus:
        """send message in conversation"""

    @abstractmethod
    async def end_conversation(self, name: str) -> None:
        """end conversation"""

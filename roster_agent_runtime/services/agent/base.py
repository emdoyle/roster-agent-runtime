from abc import ABC, abstractmethod

from roster_agent_runtime.models.agent import AgentContainer, AgentResource


def get_agent_service() -> "AgentService":
    from .docker import DockerAgentService

    return DockerAgentService()


class AgentService(ABC):
    @abstractmethod
    def create_agent(self, agent: AgentResource) -> AgentContainer:
        """create agent"""

    @abstractmethod
    def list_agents(self) -> list[AgentContainer]:
        """list agents"""

    @abstractmethod
    def get_agent(self, id: str) -> AgentContainer:
        """get agent by id"""

    @abstractmethod
    def delete_agent(self, id: str) -> AgentContainer:
        """delete agent by id"""

    @abstractmethod
    def start_agent(self, id: str) -> AgentContainer:
        """start agent by id"""

    @abstractmethod
    def stop_agent(self, id: str) -> AgentContainer:
        """stop agent by id"""

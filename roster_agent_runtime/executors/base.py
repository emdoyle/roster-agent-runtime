from abc import ABC, abstractmethod
from typing import Callable

from roster_agent_runtime.agents.base import AgentHandle
from roster_agent_runtime.executors.events import ResourceStatusEvent
from roster_agent_runtime.models.agent import AgentSpec, AgentStatus


class AgentExecutor(ABC):
    KEY = NotImplemented

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
    def get_agent_handle(self, name: str) -> AgentHandle:
        """get agent handle"""

    @abstractmethod
    def add_status_listener(self, listener: Callable[[ResourceStatusEvent], None]):
        """add listener"""

    @abstractmethod
    def remove_status_listener(self, listener: Callable[[ResourceStatusEvent], None]):
        """remove listener"""

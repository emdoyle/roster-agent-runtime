from typing import Callable

from roster_agent_runtime import errors
from roster_agent_runtime.agents import AgentHandle
from roster_agent_runtime.agents.local.handle import LocalAgentHandle
from roster_agent_runtime.models.agent import AgentSpec, AgentStatus

from .base import AgentExecutor
from .events import ResourceStatusEvent
from .store import AgentExecutorStore


class LocalAgentExecutor(AgentExecutor):
    KEY = "local"

    def __init__(self):
        self.store = AgentExecutorStore()
        self.agent_handles: dict[str, AgentHandle] = {}

    async def setup(self):
        # Local agents don't need to be setup, and there is no volatile state to check.
        # The store begins empty and the Controller is responsible for issuing CRUD to
        # reconcile it with specifications
        pass

    async def teardown(self):
        self.store.reset()
        self.agent_handles = {}

    def list_agents(self) -> list[AgentStatus]:
        return list(self.store.agents.values())

    def get_agent(self, name: str) -> AgentStatus:
        try:
            return self.store.agents[name]
        except KeyError:
            raise errors.AgentNotFoundError(agent=name)

    def _local_agent_status(self, agent: AgentSpec) -> AgentStatus:
        return AgentStatus(name=agent.name, executor=self.KEY, status="running")

    async def create_agent(self, agent: AgentSpec) -> AgentStatus:
        if agent.name in self.store.agents:
            raise errors.AgentAlreadyExistsError(agent=agent.name)

        # Agent 'image' attribute is used to identify the agent class to import
        agent_handle = LocalAgentHandle.build(name=agent.name, image=agent.image)
        self.store.agents[agent.name] = self._local_agent_status(agent=agent)
        self.agent_handles[agent.name] = agent_handle

        return self.store.agents[agent.name]

    async def update_agent(self, agent: AgentSpec) -> AgentStatus:
        if agent.name not in self.store.agents:
            raise errors.AgentNotFoundError(agent=agent.name)

        # Rebuild the agent handle in case the image has changed
        self.agent_handles[agent.name] = LocalAgentHandle.build(image=agent.image)
        return self.store.agents[agent.name]

    async def delete_agent(self, name: str) -> None:
        if name not in self.store.agents:
            raise errors.AgentNotFoundError(agent=name)

        del self.store.agents[name]
        del self.agent_handles[name]

    def get_agent_handle(self, name: str) -> AgentHandle:
        try:
            return self.agent_handles[name]
        except KeyError:
            raise errors.AgentNotFoundError(agent=name)

    def add_status_listener(self, listener: Callable[[ResourceStatusEvent], None]):
        self.store.add_status_listener(listener)

    def remove_status_listener(self, listener: Callable[[ResourceStatusEvent], None]):
        self.store.remove_status_listener(listener)

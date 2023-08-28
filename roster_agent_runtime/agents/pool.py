import asyncio
from itertools import chain
from typing import Callable

from roster_agent_runtime import errors
from roster_agent_runtime.agents import AgentHandle
from roster_agent_runtime.executors import AgentExecutor
from roster_agent_runtime.executors.events import ResourceStatusEvent
from roster_agent_runtime.models.agent import AgentSpec, AgentStatus


class AgentPool:
    def __init__(self, executors: list[AgentExecutor]):
        self.executors: dict[str, AgentExecutor] = {
            executor.KEY: executor for executor in executors
        }

    async def setup(self):
        await asyncio.gather(
            *(executor.setup() for executor in self.executors.values())
        )

    async def teardown(self):
        await asyncio.gather(
            *(executor.teardown() for executor in self.executors.values())
        )

    def list_agents(self) -> list[AgentStatus]:
        return list(
            chain(*(executor.list_agents() for executor in self.executors.values()))
        )

    def get_agent(self, name: str) -> AgentStatus:
        for executor in self.executors.values():
            try:
                return executor.get_agent(name)
            except errors.AgentError:
                pass
        raise errors.AgentNotFoundError(agent=name)

    async def create_agent(self, agent: AgentSpec) -> AgentStatus:
        return await self.executors[agent.executor].create_agent(agent)

    async def update_agent(self, agent: AgentSpec) -> AgentStatus:
        return await self.executors[agent.executor].update_agent(agent)

    async def delete_agent(self, name: str) -> None:
        agent_status = self.get_agent(name)
        await self.executors[agent_status.executor].delete_agent(name)

    def get_agent_handle(self, name: str) -> AgentHandle:
        agent_status = self.get_agent(name)
        return self.executors[agent_status.executor].get_agent_handle(name)

    def add_status_listener(self, listener: Callable[[ResourceStatusEvent], None]):
        # Add listener to all executors
        for executor in self.executors.values():
            executor.add_status_listener(listener)

    def remove_status_listener(self, listener: Callable[[ResourceStatusEvent], None]):
        # Remove listener from all executors
        for executor in self.executors.values():
            executor.remove_status_listener(listener)

from typing import Callable

from roster_agent_runtime import errors
from roster_agent_runtime.executors.base import AgentExecutor
from roster_agent_runtime.executors.events import ExecutorStatusEvent
from roster_agent_runtime.models.agent import AgentContainer, AgentSpec, AgentStatus
from roster_agent_runtime.models.conversation import ConversationMessage


def get_mock_container(image: str = "langchain-roster") -> AgentContainer:
    return AgentContainer(
        id="mock-container-id",
        name="mock-container-name",
        image=image,
        status="running",
        labels={},
    )


# TODO: this is out-of-date, doesn't use Store
class MockAgentExecutor(AgentExecutor):
    def __init__(self):
        self.agents: dict[str, AgentStatus] = {}
        self.event_listeners: list[Callable] = []

    async def setup(self):
        pass

    async def teardown(self):
        pass

    def list_agents(self) -> list[AgentStatus]:
        return list(self.agents.values())

    def get_agent(self, name: str) -> AgentStatus:
        try:
            return self.agents[name]
        except KeyError:
            raise errors.AgentNotFoundError(agent=name)

    def add_agent(self, spec: AgentSpec):
        self.agents[spec.name] = AgentStatus(
            name=spec.name,
            status="running",
            container=get_mock_container(image=spec.image),
        )

    async def create_agent(
        self, agent: AgentSpec, wait_for_healthy: bool = True
    ) -> AgentStatus:
        if agent.name in self.agents:
            raise errors.AgentAlreadyExistsError(agent=agent.name)

        self.add_agent(agent)

        return self.agents[agent.name]

    async def update_agent(self, agent: AgentSpec) -> AgentStatus:
        try:
            await self.delete_agent(agent.name)
        except errors.RosterError:
            raise errors.RosterError(f"Could not update agent {agent.name}.")

        return await self.create_agent(agent)

    async def delete_agent(self, name: str) -> None:
        try:
            running_agent = self.agents.pop(name)
        except KeyError:
            raise errors.AgentNotFoundError(agent=name)

    async def prompt(
        self,
        name: str,
        history: list[ConversationMessage],
        message: ConversationMessage,
    ) -> ConversationMessage:
        return ConversationMessage(
            message="Hello, world",
            sender="mock_agent_executor",
        )

    def add_event_listener(self, listener: Callable[[ExecutorStatusEvent], None]):
        self.event_listeners.append(listener)

    def remove_event_listener(self, listener: Callable[[ExecutorStatusEvent], None]):
        self.event_listeners.remove(listener)

    # Methods below are meant to be used by the test suite

    def set_agents(self, agents: dict[str, AgentStatus]):
        self.agents = agents

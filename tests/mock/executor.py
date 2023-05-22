from typing import Callable

from roster_agent_runtime.controllers.agent import errors
from roster_agent_runtime.executors.base import AgentExecutor
from roster_agent_runtime.executors.docker import RunningAgent
from roster_agent_runtime.models.agent import (
    AgentCapabilities,
    AgentContainer,
    AgentSpec,
    AgentStatus,
)
from roster_agent_runtime.models.conversation import ConversationMessage
from roster_agent_runtime.models.task import TaskSpec, TaskStatus


def get_mock_container(image: str = "langchain-roster") -> AgentContainer:
    return AgentContainer(
        id="mock-container-id",
        name="mock-container-name",
        image=image,
        status="running",
        labels={},
        capabilities=AgentCapabilities(network_access=True),
    )


class MockAgentExecutor(AgentExecutor):
    def __init__(self):
        self.agents: dict[str, RunningAgent] = {}
        self.tasks: dict[str, TaskStatus] = {}
        self.agent_status_listeners: list[Callable] = []
        self.task_status_listeners: list[Callable] = []

    async def setup(self):
        pass

    async def teardown(self):
        pass

    def list_agents(self) -> list[AgentStatus]:
        return [agent.status for agent in self.agents.values()]

    def get_agent(self, name: str) -> AgentStatus:
        try:
            return self.agents[name].status
        except KeyError:
            raise errors.AgentNotFoundError(agent=name)

    def add_agent(self, spec: AgentSpec):
        self.agents[spec.name] = RunningAgent(
            status=AgentStatus(
                name=spec.name,
                status="running",
                container=get_mock_container(image=spec.image),
            )
        )

    async def create_agent(
        self, agent: AgentSpec, wait_for_healthy: bool = True
    ) -> AgentStatus:
        if agent.name in self.agents:
            raise errors.AgentAlreadyExistsError(agent=agent.name)

        self.add_agent(agent)

        return self.agents[agent.name].status

    async def update_agent(self, agent: AgentSpec) -> AgentStatus:
        try:
            await self.delete_agent(agent.name)
        except errors.AgentServiceError:
            raise errors.AgentServiceError(f"Could not update agent {agent.name}.")

        return await self.create_agent(agent)

    async def delete_agent(self, name: str) -> None:
        try:
            running_agent = self.agents.pop(name)
            for task in running_agent.tasks.values():
                self.tasks.pop(task.name, None)
        except KeyError:
            raise errors.AgentNotFoundError(agent=name)

    def _store_task(self, agent_name: str, task: TaskStatus):
        self.agents[agent_name].tasks[task.name] = task
        self.tasks[task.name] = task

    async def initiate_task(self, task: TaskSpec) -> TaskStatus:
        if task.name in self.tasks:
            raise errors.TaskAlreadyExistsError(task=task.name)

        self._store_task(
            task.agent_name,
            TaskStatus(
                name=task.name,
                agent_name=task.agent_name,
                status="running",
            ),
        )

        return self.tasks[task.name]

    async def update_task(self, task: TaskSpec) -> TaskStatus:
        try:
            await self.end_task(task.name)
        except errors.TaskNotFoundError:
            raise errors.TaskNotFoundError(task=task.name)

        return await self.initiate_task(task)

    def list_tasks(self) -> list[TaskStatus]:
        return list(self.tasks.values())

    def get_task(self, task: TaskSpec) -> TaskStatus:
        try:
            return self.tasks[task.name]
        except KeyError:
            raise errors.TaskNotFoundError(task=task.name)

    async def end_task(self, name: str) -> None:
        try:
            task = self.tasks.pop(name)
            self.agents[task.agent_name].tasks.pop(name)
        except KeyError:
            raise errors.TaskNotFoundError(task=name)

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

    def add_agent_status_listener(self, listener: Callable):
        self.agent_status_listeners.append(listener)

    def add_task_status_listener(self, listener: Callable):
        self.task_status_listeners.append(listener)

    # Methods below are meant to be used by the test suite

    def set_agents(self, agents: dict[str, RunningAgent]):
        self.agents = agents

    def set_tasks(self, tasks: dict[str, TaskStatus]):
        self.tasks = tasks

    def send_agent_status(self, agent: AgentStatus):
        for listener in self.agent_status_listeners:
            listener(agent)

    def send_task_status(self, task: TaskStatus):
        for listener in self.task_status_listeners:
            listener(task)

from roster_agent_runtime.executors.base import AgentExecutor
from roster_agent_runtime.models.agent import AgentResource, AgentSpec, AgentStatus
from roster_agent_runtime.models.conversation import (
    ConversationMessage,
    ConversationResource,
    ConversationSpec,
    ConversationStatus,
)
from roster_agent_runtime.models.task import TaskResource, TaskSpec, TaskStatus
from roster_agent_runtime.services.agent import errors
from roster_agent_runtime.services.agent.base import AgentService


class LocalAgentService(AgentService):
    def __init__(self, executor: AgentExecutor):
        # TODO: properly abstract executor per-Agent
        self.executor = executor
        self.setup_status_listeners()
        self.agents: dict[str, AgentResource] = {}
        self.tasks: dict[str, TaskResource] = {}
        self.conversations: dict[str, ConversationResource] = {}

    def _task_status_listener(self, task: TaskStatus):
        try:
            self.tasks[task.name].status = task
        except KeyError:
            pass

    def _agent_status_listener(self, agent: AgentStatus):
        try:
            self.agents[agent.name].status = agent
        except KeyError:
            pass

    def setup_status_listeners(self):
        self.executor.add_task_status_listener(self._task_status_listener)
        self.executor.add_agent_status_listener(self._agent_status_listener)

    async def create_agent(self, agent: AgentSpec) -> AgentStatus:
        if agent.name in self.agents:
            raise errors.AgentAlreadyExistsError(agent=agent.name)
        agent_status = await self.executor.create_agent(agent)
        agent_resource = AgentResource(spec=agent, status=agent_status)
        self.agents[agent.name] = agent_resource
        return agent_status

    async def update_agent(self, agent: AgentSpec) -> AgentStatus:
        if agent.name not in self.agents:
            raise errors.AgentNotFoundError(agent=agent.name)
        agent_status = await self.executor.update_agent(agent)
        self.agents[agent.name].status = agent_status
        return agent_status

    async def list_agents(self) -> list[AgentStatus]:
        return list(map(lambda agent: agent.status, self.agents.values()))

    async def get_agent(self, name: str) -> AgentStatus:
        try:
            return self.agents[name].status
        except KeyError as e:
            raise errors.AgentNotFoundError(agent=name) from e

    async def delete_agent(self, name: str) -> None:
        try:
            agent = self.agents.pop(name)
        except KeyError as e:
            raise errors.AgentNotFoundError(agent=name) from e

        return await self.executor.delete_agent(agent.spec)

    async def initiate_task(self, task: TaskSpec) -> TaskStatus:
        if task.name in self.tasks:
            raise errors.TaskAlreadyExistsError(task=task.name)
        if task.agent_name not in self.agents:
            raise errors.AgentNotFoundError(agent=task.agent_name)

        task_status = await self.executor.initiate_task(task)
        self.tasks[task.name] = TaskResource(spec=task, status=task_status)

        return task_status

    async def start_conversation(
        self, conversation: ConversationSpec
    ) -> ConversationStatus:
        if conversation.name in self.conversations:
            raise errors.ConversationAlreadyExistsError(conversation=conversation.name)
        if conversation.agent_name not in self.agents:
            raise errors.AgentNotFoundError(agent=conversation.agent_name)

        conversation_status = ConversationStatus(status="running")
        self.conversations[conversation.name] = ConversationResource(
            spec=conversation, status=conversation_status
        )
        return conversation_status

    async def prompt(
        self, name: str, conversation_message: ConversationMessage
    ) -> ConversationMessage:
        try:
            conversation = self.conversations[name]
        except KeyError as e:
            raise errors.ConversationNotFoundError(conversation=name) from e
        if conversation.spec.agent_name not in self.agents:
            raise errors.AgentNotFoundError(agent=conversation.spec.agent_name)
        if conversation.status != "running":
            raise errors.ConversationNotAvailableError(conversation=name)

        return await self.executor.prompt(conversation, conversation_message)

    async def end_conversation(self, name: str) -> None:
        try:
            conversation = self.conversations.pop(name)
        except KeyError as e:
            raise errors.ConversationNotFoundError(conversation=name) from e
        if conversation.status != "running":
            raise errors.ConversationNotAvailableError(conversation=name)

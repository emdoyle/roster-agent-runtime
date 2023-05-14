from roster_agent_runtime.executors.base import AgentExecutor
from roster_agent_runtime.models.agent import AgentResource
from roster_agent_runtime.models.conversation import (
    ConversationPrompt,
    ConversationResource,
)
from roster_agent_runtime.models.task import TaskResource
from roster_agent_runtime.services.agent import errors
from roster_agent_runtime.services.agent.base import AgentService


class LocalAgentService(AgentService):
    def __init__(self, executor: AgentExecutor):
        self.executor = executor
        self.agents: dict[str, AgentResource] = {}
        self.tasks: dict[str, TaskResource] = {}
        self.conversations: dict[str, ConversationResource] = {}

    async def create_agent(self, agent: AgentResource) -> AgentResource:
        if agent.name in self.agents:
            raise errors.AgentAlreadyExistsError(agent=agent.name)
        self.agents[agent.name] = self.executor.create_agent(agent)
        return self.agents[agent.name]

    async def list_agents(self) -> list[AgentResource]:
        return list(self.agents.values())

    async def get_agent(self, name: str) -> AgentResource:
        try:
            return self.agents[name]
        except KeyError as e:
            raise errors.AgentNotFoundError(agent=name) from e

    async def delete_agent(self, name: str) -> AgentResource:
        try:
            agent = self.agents.pop(name)
        except KeyError as e:
            raise errors.AgentNotFoundError(agent=name) from e

        return self.executor.delete_agent(agent)

    async def initiate_task(self, task: TaskResource) -> TaskResource:
        """if the agent exists, use the AgentResource to run a container for the task"""
        if task.id in self.tasks:
            raise errors.TaskAlreadyExistsError(task=task.id)
        if task.agent_name not in self.agents:
            raise errors.AgentNotFoundError(agent=task.agent_name)

        return self.executor.initiate_task(task)

    async def start_conversation(
        self, conversation: ConversationResource
    ) -> ConversationResource:
        if conversation.id in self.conversations:
            raise errors.ConversationAlreadyExistsError(conversation=conversation.id)
        if conversation.agent_name not in self.agents:
            raise errors.AgentNotFoundError(agent=conversation.agent_name)

        # TODO: don't accept 'status' from API request
        conversation.status = "running"
        self.conversations[conversation.id] = conversation
        return conversation

    async def prompt(
        self, conversation_id: str, conversation_prompt: ConversationPrompt
    ) -> ConversationResource:
        try:
            conversation = self.conversations[conversation_id]
        except KeyError as e:
            raise errors.ConversationNotFoundError(conversation=conversation_id) from e
        if conversation.agent_name != conversation_prompt.agent_name:
            raise errors.InvalidRequestError("Conversation and prompt agent mismatch.")
        if conversation.agent_name not in self.agents:
            raise errors.AgentNotFoundError(agent=conversation.agent_name)
        if conversation.status != "running":
            raise errors.ConversationNotAvailableError(conversation=conversation_id)

        return self.executor.prompt(conversation, conversation_prompt)

    async def end_conversation(self, conversation_id: str) -> ConversationResource:
        try:
            conversation = self.conversations.pop(conversation_id)
        except KeyError as e:
            raise errors.ConversationNotFoundError(conversation=conversation_id) from e
        if conversation.status != "running":
            raise errors.ConversationNotAvailableError(conversation=conversation_id)

        # NOTE: conversation is deleted in state, might be confusing to return it
        conversation.status = "ended"
        return conversation

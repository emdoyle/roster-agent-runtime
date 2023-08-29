import importlib
from typing import AsyncIterator

from roster_agent_runtime import errors
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.conversation import ConversationMessage
from roster_agent_runtime.models.messaging import OutgoingMessage

from ..base import AgentHandle
from .base import LocalAgent

logger = app_logger()


class LocalAgentHandle(AgentHandle):
    def __init__(self, agent: LocalAgent):
        self.agent = agent

    @classmethod
    def build(
        cls, name: str, package: str = "roster_agent_runtime.agents.local"
    ) -> "LocalAgentHandle":
        # dynamic import of agent module from name
        try:
            module = importlib.import_module(f"{package}.{name}")
        except ImportError:
            raise errors.AgentNotFoundError(agent=name)

        # get the agent class from the module
        try:
            agent_class = getattr(module, "AGENT_CLASS")
        except AttributeError:
            raise errors.AgentNotFoundError(agent=name)

        # check that the agent class is a subclass of LocalAgent
        try:
            assert issubclass(agent_class, LocalAgent)
        except AssertionError:
            raise errors.AgentNotFoundError(agent=name)

        # instantiate the agent class
        agent = agent_class()
        return cls(agent=agent)

    async def chat(
        self,
        identity: str,
        team: str,
        role: str,
        chat_history: list[ConversationMessage],
        execution_id: str = "",
        execution_type: str = "",
    ) -> str:
        return await self.agent.chat(
            identity=identity,
            team=team,
            role=role,
            chat_history=chat_history,
            execution_id=execution_id,
            execution_type=execution_type,
        )

    async def trigger_action(
        self,
        action: str,
        inputs: dict[str, str],
        role_context: str,
        record_id: str,
        workflow: str,
    ) -> None:
        await self.agent.trigger_action(
            action=action,
            inputs=inputs,
            role_context=role_context,
            record_id=record_id,
            workflow=workflow,
        )

    async def outgoing_message_stream(self) -> AsyncIterator[OutgoingMessage]:
        async for message in self.agent.outgoing_message_stream():
            yield message

    async def activity_stream(self) -> AsyncIterator[dict]:
        async for activity in self.agent.activity_stream():
            yield activity

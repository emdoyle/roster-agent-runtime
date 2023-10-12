import importlib
from typing import AsyncIterator

from roster_agent_runtime import errors
from roster_agent_runtime.agents.base import AgentHandle
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.conversation import ConversationMessage
from roster_agent_runtime.models.messaging import OutgoingMessage

from .base import LocalAgent

logger = app_logger()


class LocalAgentHandle(AgentHandle):
    def __init__(self, agent: LocalAgent):
        self.agent = agent

    @classmethod
    def build(
        cls, name: str, image: str, package: str = "roster_agent_runtime.agents.local"
    ) -> "LocalAgentHandle":
        # dynamic import of agent module from name
        try:
            module = importlib.import_module(f"{package}.{image}")
        except (ModuleNotFoundError, ImportError):
            raise errors.AgentNotFoundError(agent=image)

        # get the agent class from the module
        try:
            agent_class = getattr(module, "AGENT_CLASS")
        except AttributeError:
            raise errors.AgentNotFoundError(agent=image)

        # check that the agent class is a subclass of LocalAgent
        try:
            assert issubclass(agent_class, LocalAgent)
        except AssertionError:
            raise errors.AgentNotFoundError(agent=image)

        # instantiate the agent class
        agent = agent_class(name=name, namespace="default")
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
        step: str,
        action: str,
        inputs: dict[str, str],
        role_context: str,
        record_id: str,
        workflow: str,
    ) -> None:
        await self.agent.trigger_action(
            step=step,
            action=action,
            inputs=inputs,
            role_context=role_context,
            record_id=record_id,
            workflow=workflow,
        )

    async def handle_tool_response(
        self, invocation_id: str, tool: str, data: dict
    ) -> None:
        await self.agent.handle_tool_response(
            invocation_id=invocation_id, tool=tool, data=data
        )

    # NOTE: should only have one consumer on a stream like this
    async def outgoing_message_stream(self) -> AsyncIterator[OutgoingMessage]:
        async for message in self.agent.outgoing_message_stream():
            yield message

    # NOTE: should only have one consumer on a stream like this
    async def activity_stream(self) -> AsyncIterator[dict]:
        async for activity in self.agent.activity_stream():
            yield activity

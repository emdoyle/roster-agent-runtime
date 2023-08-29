import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from roster_agent_runtime import errors
from roster_agent_runtime.models.conversation import ConversationMessage
from roster_agent_runtime.models.messaging import OutgoingMessage

from .actions.base import LocalAgentAction


class LocalAgent(ABC):
    @abstractmethod
    async def chat(
        self,
        identity: str,
        team: str,
        role: str,
        chat_history: list[ConversationMessage],
        execution_id: str = "",
        execution_type: str = "",
    ) -> str:
        ...

    @abstractmethod
    async def trigger_action(
        self,
        action: str,
        inputs: dict[str, str],
        role_context: str,
        record_id: str,
        workflow: str,
    ) -> None:
        ...

    # ASYNCITERDEF: 'def' in interface only to workaround type hint deficiency
    #   AsyncIterator needs 'yield' keyword in implementation (absent in interface)
    @abstractmethod
    def outgoing_message_stream(self) -> AsyncIterator[OutgoingMessage]:
        ...

    # ASYNCITERDEF: 'def' in interface only to workaround type hint deficiency
    #   AsyncIterator needs 'yield' keyword in implementation (absent in interface)
    @abstractmethod
    def activity_stream(self) -> AsyncIterator[dict]:
        ...


class BaseLocalAgent(LocalAgent):
    NAME: str = NotImplemented
    ACTIONS: list[LocalAgentAction] = NotImplemented
    AGENT_CONTEXT: dict = NotImplemented

    def __init__(self, *args, **kwargs):
        self._outgoing_message_queue = asyncio.Queue()
        self._activity_stream_queue = asyncio.Queue()

    async def chat(
        self,
        identity: str,
        team: str,
        role: str,
        chat_history: list[ConversationMessage],
        execution_id: str = "",
        execution_type: str = "",
    ) -> str:
        raise NotImplementedError(f"chat not implemented for agent: {self.NAME}")

    async def trigger_action(
        self,
        action: str,
        inputs: dict[str, str],
        role_context: str,
        record_id: str,
        workflow: str,
    ) -> None:
        action_class = next(
            (
                action_class
                for action_class in self.ACTIONS
                if action_class.KEY == action
            ),
            None,
        )
        if action_class is None:
            raise errors.AgentError(f"Unknown action: {action} for agent: {self.NAME}")

        action_output: Optional[dict] = None
        action_error: str = ""
        try:
            action_output = await action_class().execute(inputs, context=role_context)
        except Exception as e:
            action_error = str(e)

        outgoing_message = OutgoingMessage.workflow_action_result(
            record_id=record_id,
            workflow=workflow,
            action=action,
            outputs=action_output,
            error=action_error,
        )
        await self._outgoing_message_queue.put(outgoing_message)

    async def outgoing_message_stream(self) -> AsyncIterator[OutgoingMessage]:
        while True:
            yield await self._outgoing_message_queue.get()

    async def activity_stream(self) -> AsyncIterator[dict]:
        while True:
            yield await self._activity_stream_queue.get()

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import AsyncIterator

import pydantic
from roster_agent_runtime import errors
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.conversation import ConversationMessage
from roster_agent_runtime.models.files import FileContents
from roster_agent_runtime.models.messaging import (
    OutgoingMessage,
    ReadFileResponsePayload,
)

from .actions.base import LocalAgentAction

logger = app_logger()


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
        step: str,
        action: str,
        inputs: dict[str, str],
        role_context: str,
        record_id: str,
        workflow: str,
    ) -> None:
        ...

    @abstractmethod
    async def handle_tool_response(
        self, invocation_id: str, tool: str, data: dict
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
        self._pending_tool_invocations: dict[str, asyncio.Future] = {}
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
        step: str,
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

        action_output: dict[str, str] = {}
        action_error: str = ""
        try:
            action_output = await action_class().execute(inputs, context=role_context)
        except Exception as e:
            action_error = str(e)

        outgoing_message = OutgoingMessage.workflow_action_result(
            record_id=record_id,
            workflow=workflow,
            step=step,
            action=action,
            outputs=action_output,
            error=action_error,
        )
        await self._outgoing_message_queue.put(outgoing_message)

    async def read_files(
        self, filepaths: list[str], record_id: str, workflow: str
    ) -> list[FileContents]:
        response = await self.invoke_tool(
            tool="workspace-file-reader",
            inputs={
                "filepaths": filepaths,
                "record_id": record_id,
                "workflow": workflow,
            },
        )
        try:
            result = ReadFileResponsePayload(**response)
        except pydantic.ValidationError as e:
            logger.debug(
                "(local-agent) Failed to parse ReadFileResponsePayload: %s; %s",
                response,
                e,
            )
            raise errors.AgentError(
                "Failed to parse response from workspace file reader"
            )

        return result.files

    async def invoke_tool(self, tool: str, inputs: dict) -> dict:
        invocation_id = str(uuid.uuid4())
        tool_response_future = asyncio.Future()
        self._pending_tool_invocations[invocation_id] = tool_response_future

        outgoing_message = OutgoingMessage.tool_invocation(
            invocation_id=invocation_id, tool=tool, inputs=inputs
        )
        await self._outgoing_message_queue.put(outgoing_message)

        return await tool_response_future

    async def handle_tool_response(
        self, invocation_id: str, tool: str, data: dict
    ) -> None:
        future = self._pending_tool_invocations.pop(invocation_id, None)
        if future is None:
            logger.debug(
                "(local-agent) no pending invocation for id: %s", invocation_id
            )
            return

        logger.debug(
            "(local-agent) resolving pending invocation for id: %s", invocation_id
        )
        future.set_result(data)

    async def outgoing_message_stream(self) -> AsyncIterator[OutgoingMessage]:
        while True:
            yield await self._outgoing_message_queue.get()

    async def activity_stream(self) -> AsyncIterator[dict]:
        while True:
            yield await self._activity_stream_queue.get()

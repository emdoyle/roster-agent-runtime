from abc import ABC, abstractmethod
from typing import AsyncIterator

from roster_agent_runtime.models.conversation import ConversationMessage
from roster_agent_runtime.models.messaging import OutgoingMessage


class AgentHandle(ABC):
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
        """Respond to a prompt"""

    @abstractmethod
    async def trigger_action(
        self,
        action: str,
        inputs: dict[str, str],
        role_context: str,
        record_id: str,
        workflow: str,
    ) -> None:
        """Trigger an Action implemented by the Agent"""

    # ASYNCITERDEF: 'def' in interface only to workaround type hint deficiency
    #   AsyncIterator needs 'yield' keyword in implementation (absent in interface)
    @abstractmethod
    def outgoing_message_stream(self) -> AsyncIterator[OutgoingMessage]:
        """Stream outgoing messages sent by the Agent to another inbox"""

    # ASYNCITERDEF: 'def' in interface only to workaround type hint deficiency
    #   AsyncIterator needs 'yield' keyword in implementation (absent in interface)
    @abstractmethod
    def activity_stream(self) -> AsyncIterator[dict]:
        """Stream activities from the agent"""

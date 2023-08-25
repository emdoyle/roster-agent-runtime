from abc import ABC, abstractmethod
from typing import AsyncIterator

from roster_agent_runtime.models.conversation import ConversationMessage


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
    def activity_stream(self) -> AsyncIterator[dict]:
        """Stream activities from the agent"""

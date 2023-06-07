from abc import ABC, abstractmethod

from roster_agent_runtime.models.conversation import ConversationMessage
from roster_agent_runtime.models.task import TaskStatus


class AgentHandle(ABC):
    @abstractmethod
    async def chat(
        self, chat_history: list[ConversationMessage]
    ) -> ConversationMessage:
        """Respond to a prompt"""

    @abstractmethod
    async def execute_task(self, name: str, description: str) -> None:
        """Execute a task on the agent"""

    @abstractmethod
    async def update_task(self, name: str, description: str) -> None:
        """Update the description of a task"""

    @abstractmethod
    async def list_tasks(self) -> list[TaskStatus]:
        """List the tasks running on the agent"""

    @abstractmethod
    async def get_task(self, task: str) -> TaskStatus:
        """Get the status of a task"""

    @abstractmethod
    async def cancel_task(self, task: str) -> None:
        """Cancel a task"""

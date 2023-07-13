from abc import ABC, abstractmethod
from typing import AsyncIterator

from roster_agent_runtime.models.conversation import ConversationMessage
from roster_agent_runtime.models.task import TaskAssignment, TaskStatus


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
    async def execute_task(
        self, name: str, description: str, assignment: TaskAssignment
    ) -> None:
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

    @abstractmethod
    def activity_stream(self) -> AsyncIterator[dict]:
        """Stream activities from the agent"""

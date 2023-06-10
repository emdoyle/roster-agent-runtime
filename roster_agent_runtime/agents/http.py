import aiohttp
import pydantic
from roster_agent_runtime import errors
from roster_agent_runtime.models.conversation import ConversationMessage
from roster_agent_runtime.models.task import TaskAssignment, TaskStatus

from .base import AgentHandle


class HttpAgentHandle(AgentHandle):
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url

    @classmethod
    def build(cls, name: str, url: str) -> "HttpAgentHandle":
        # Any other logic here? validation?
        return cls(name=name, url=url)

    async def _request(
        self, method: str, url: str, *, raise_for_status: bool = True, **kwargs
    ) -> dict:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, **kwargs) as response:
                    if raise_for_status:
                        assert response.status == 200
                    return await response.json()
        except AssertionError as e:
            raise errors.TaskError("Agent returned an error.") from e
        except aiohttp.ClientError as e:
            raise errors.TaskError(f"Could not connect to agent {self.name}.") from e

    async def chat(
        self, chat_history: list[ConversationMessage]
    ) -> ConversationMessage:
        try:
            response_data = await self._request(
                "POST",
                f"{self.url}/chat",
                json=[message.dict() for message in chat_history],
            )
            return ConversationMessage(**response_data)
        except pydantic.ValidationError as e:
            raise errors.TaskError(
                f"Could not parse chat response from agent {self.name}."
            ) from e

    async def execute_task(
        self, name: str, description: str, assignment: TaskAssignment
    ) -> None:
        await self._request(
            "POST",
            f"{self.url}/tasks",
            json={
                "task": name,
                "description": description,
                "assignment": assignment.dict(),
            },
        )

    async def update_task(self, name: str, description: str) -> None:
        await self._request(
            "PATCH",
            f"{self.url}/tasks/{name}",
            json={"name": name, "description": description},
        )

    async def list_tasks(self) -> list[TaskStatus]:
        try:
            response_data = await self._request("GET", f"{self.url}/tasks")
            return [TaskStatus(**task_status) for task_status in response_data]
        except (TypeError, pydantic.ValidationError) as e:
            raise errors.TaskError(
                f"Could not parse response from agent {self.name}."
            ) from e

    async def get_task(self, task: str) -> TaskStatus:
        try:
            response_data = await self._request("GET", f"{self.url}/tasks/{task}")
            return TaskStatus(**response_data)
        except pydantic.ValidationError as e:
            raise errors.TaskError(
                f"Could not parse response from agent {self.name}."
            ) from e

    async def cancel_task(self, task: str) -> None:
        await self._request("DELETE", f"{self.url}/tasks/{task}")

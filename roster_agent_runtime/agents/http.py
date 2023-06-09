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

    async def _request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, **kwargs) as response:
                    return response
        except aiohttp.ClientError as e:
            raise errors.TaskError(f"Could not connect to agent {self.name}.") from e

    async def chat(
        self, chat_history: list[ConversationMessage]
    ) -> ConversationMessage:
        try:
            response = await self._request(
                "POST",
                f"{self.url}/chat",
                json=[message.dict() for message in chat_history],
            )
            assert response.status == 200
            response_text = await response.text()
            return ConversationMessage(message=response_text, sender=self.name)
        except AssertionError as e:
            raise errors.TaskError(f"Could not chat with agent {self.name}.") from e
        except (pydantic.ValidationError, aiohttp.ContentTypeError) as e:
            raise errors.TaskError(
                f"Could not parse response from agent {self.name}."
            ) from e

    async def execute_task(
        self, name: str, description: str, assignment: TaskAssignment
    ) -> None:
        try:
            response = await self._request(
                "POST",
                f"{self.url}/tasks",
                json={
                    "name": name,
                    "description": description,
                    "assignment": assignment.dict(),
                },
            )
            assert response.status == 200
        except AssertionError as e:
            raise errors.TaskError(
                f"Could not execute task {name} on agent {self.name}."
            ) from e

    async def update_task(self, name: str, description: str) -> None:
        try:
            response = await self._request(
                "PATCH",
                f"{self.url}/tasks/{name}",
                json={"name": name, "description": description},
            )
            assert response.status == 200
        except AssertionError as e:
            raise errors.TaskError(
                f"Could not update task {name} on agent {self.name}."
            ) from e

    async def list_tasks(self) -> list[TaskStatus]:
        try:
            response = await self._request("GET", f"{self.url}/tasks")
            assert response.status == 200
            return [TaskStatus(**task_status) for task_status in await response.json()]
        except AssertionError as e:
            raise errors.TaskError(
                f"Could not fetch task status from agent {self.name}."
            ) from e
        except (pydantic.ValidationError, aiohttp.ContentTypeError) as e:
            raise errors.TaskError(
                f"Could not parse response from agent {self.name}."
            ) from e

    async def get_task(self, task: str) -> TaskStatus:
        try:
            response = await self._request("GET", f"{self.url}/tasks/{task}")
            assert response.status == 200
            return TaskStatus(**await response.json())
        except AssertionError as e:
            raise errors.TaskError(
                f"Could not fetch task status from agent {self.name}."
            ) from e
        except (pydantic.ValidationError, aiohttp.ContentTypeError) as e:
            raise errors.TaskError(
                f"Could not parse response from agent {self.name}."
            ) from e

    async def cancel_task(self, task: str) -> None:
        try:
            response = await self._request("DELETE", f"{self.url}/tasks/{task}")
            assert response.status == 200
        except AssertionError as e:
            raise errors.TaskError(
                f"Could not cancel task {task} on agent {self.name}."
            ) from e

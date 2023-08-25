import json
from typing import AsyncIterator

import aiohttp
import pydantic
from roster_agent_runtime import errors
from roster_agent_runtime.models.conversation import ConversationMessage

from ..constants import EXECUTION_ID_HEADER, EXECUTION_TYPE_HEADER
from ..logs import app_logger
from .base import AgentHandle

logger = app_logger()


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
            raise errors.AgentError("Agent returned an error.") from e
        except aiohttp.ClientError as e:
            raise errors.AgentError(f"Could not connect to agent {self.name}.") from e

    async def chat(
        self,
        identity: str,
        team: str,
        role: str,
        chat_history: list[ConversationMessage],
        execution_id: str = "",
        execution_type: str = "",
    ) -> str:
        try:
            headers = {}
            if execution_id:
                headers[EXECUTION_ID_HEADER] = execution_id
            if execution_type:
                headers[EXECUTION_TYPE_HEADER] = execution_type
            payload = {
                "identity": identity,
                "team": team,
                "role": role,
                "messages": [message.dict() for message in chat_history],
            }
            response_data = await self._request(
                "POST",
                f"{self.url}/chat",
                json=payload,
                headers=headers,
            )
            return response_data["message"]
        except (KeyError, pydantic.ValidationError) as e:
            raise errors.AgentError(
                f"Could not parse chat response from agent {self.name}."
            ) from e

    async def activity_stream(self) -> AsyncIterator[dict]:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.url}/activity-stream") as resp:
                async for line in resp.content:
                    if line == b"\n":
                        continue
                    logger.debug(
                        "(agent-handle) Received activity event (agent %s) %s",
                        self.name,
                        line,
                    )
                    decoded = line.decode("utf-8").strip()
                    try:
                        yield json.loads(json.loads(decoded))
                    except json.JSONDecodeError:
                        logger.debug(
                            "(agent-handle) Skipping malformed activity event (agent %s) %s",
                            self.name,
                            decoded,
                        )
                        pass

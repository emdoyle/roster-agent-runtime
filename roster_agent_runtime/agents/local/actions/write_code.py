from typing import Optional

from roster_agent_runtime.agents.local.actions.base import LocalAgentAction


class WriteCode(LocalAgentAction):
    async def execute(
        self, inputs: dict[str, str], context: Optional[dict] = None
    ) -> dict[str, str]:
        return {"code": "print('Hello, World!')"}

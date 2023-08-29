from roster_agent_runtime.agents.local.actions.base import LocalAgentAction


class WriteCode(LocalAgentAction):
    KEY = "WriteCode"

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        return {"code": "print('Hello, World!')"}
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.common import TypedArgument

from .base import BaseLocalAgentAction

logger = app_logger()


PROMPT_TEMPLATE = """"""


class IdentifyDomains(BaseLocalAgentAction):
    KEY = "IdentifyDomains"
    SIGNATURE = (
        (TypedArgument.text("codebase_tree"),),
        (TypedArgument.text("domains"),),
    )

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        try:
            codebase_tree = inputs["codebase_tree"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")

        self.store_output("TODO")
        return {"domains": "TODO"}

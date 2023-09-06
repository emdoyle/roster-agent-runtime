from roster_agent_runtime.agents.local.actions.base import LocalAgentAction


class DummyPlanCodeChanges(LocalAgentAction):
    KEY = "PlanCodeChanges"

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        with open("plan_code_changes_output.txt", "r") as f:
            plan = f.read()
            return {"implementation_plan": plan}


class PlanCodeChanges(LocalAgentAction):
    KEY = "PlanCodeChanges"

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        ...

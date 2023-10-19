from roster_agent_runtime.agents.local.actions.base import BaseLocalAgentAction
from roster_agent_runtime.agents.local.actions.write_code.planning import \
    generate_expert_implementation_plan
from roster_agent_runtime.agents.local.parsers.codebase_tree import \
    CodebaseTreeParser
from roster_agent_runtime.agents.local.parsers.experts import ExpertsParser
from roster_agent_runtime.agents.local.parsers.plan import \
    ExpertPlanInstructionsParser
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.common import TypedArgument

logger = app_logger()


class WriteCode(BaseLocalAgentAction):
    KEY = "WriteCode"
    SIGNATURE = (
        (
            TypedArgument.text("change_request"),
            TypedArgument.text("project_summary"),
            TypedArgument.text("codebase_tree"),
            TypedArgument.text("experts"),
            TypedArgument.text("expert_instructions"),
        ),
        (TypedArgument.code("code"),),
    )

    async def execute(
        self,
        inputs: dict[str, str],
        context: str = "",
    ) -> dict[str, str]:
        try:
            change_request = inputs["change_request"]
            project_summary = inputs["project_summary"]
            codebase_tree = inputs["codebase_tree"]
            experts = inputs["experts"]
            expert_instructions = inputs["expert_instructions"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")

        parsed_tree = CodebaseTreeParser.parse(codebase_tree)
        parsed_experts = ExpertsParser.parse(experts)
        parsed_expert_instructions = ExpertPlanInstructionsParser.parse(
            expert_instructions
        )

        code_outputs = []
        for parsed_instructions in parsed_expert_instructions:
            expert = next(
                (
                    parsed_expert
                    for parsed_expert in parsed_experts
                    if parsed_expert.name == parsed_instructions.name
                )
            )
            implementation_plan = await generate_expert_implementation_plan(
                project_summary=project_summary,
                change_request=change_request,
                instructions=parsed_instructions,
                codebase_tree=parsed_tree.filtered_tree(expert.entities),
                context=context,
            )
            # implementation_results = await execute_implementation_plan(
            #     agent=self.agent,
            #     implementation_plan=implementation_plan,
            #     previous_code_outputs=code_outputs,
            # )
            # code_outputs.extend(implementation_results)

        # final_code_output = json.dumps(
        #     [code_output.dict() for code_output in code_outputs]
        # )
        # self.store_output(final_code_output)
        return {"code": "TODO"}

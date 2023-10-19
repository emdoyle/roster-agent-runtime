import json

from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.common import TypedArgument

from ..parsers.code import CodeOutput, CodeOutputParser, RefinedCodeResponseParser
from ..parsers.plan import ImplementationPlanAction, ImplementationPlanParser
from ..util.llm import ask_openai
from .base import SYSTEM_PROMPT, BaseLocalAgentAction

logger = app_logger()


PROMPT_TEMPLATE = """
Role: {role}

## Instructions
You are tasked with refining a single file which has been created or modified by another software engineer as part of an attempt to fulfill a request.
You will find the contents of this file below. You will also find the original request, along with the portion of the implementation plan which was assigned to this particular file.
If you believe that the plan has not been followed appropriately, or if there are small mistakes such as typos or missing parameters, please fix them.
Otherwise, if you believe that the plan was followed appropriately, simply respond with the exact text "OK" within XML 'code' tags as shown in the Format example.

Here are some tips:
* The file must be syntactically valid. Do NOT add any content after the last line of code.
* Pay extremely close attention to the provided implementation plan.
* Think step-by-step before writing. You may include some deliberation and planning in your response, as long as it comes before the XML tag as shown in the Format example.

-----
## Original request
{change_request}
-----
## The Plan
{plan}
-----
## The File
{original_code}
-----

## Format example
<code>
[your code here OR simply 'OK']
</code>
"""


class RefineCode(BaseLocalAgentAction):
    KEY = "RefineCode"
    SIGNATURE = (
        (
            TypedArgument.text("change_request"),
            TypedArgument.text("implementation_plan"),
            TypedArgument.code("code"),
        ),
        (TypedArgument.code("refined_code"),),
    )

    async def _refine_code(
        self,
        role: str,
        change_request: str,
        code: CodeOutput,
        plan: ImplementationPlanAction,
    ) -> CodeOutput:
        prompt = PROMPT_TEMPLATE.format(
            role=role,
            change_request=change_request,
            original_code=code.content,
            filename=code.filepath,
            plan=plan.plan,
        )
        output = await ask_openai(prompt, SYSTEM_PROMPT)

        refined_code_content = RefinedCodeResponseParser(
            tag="code", refinement_declined_phrase="OK"
        ).parse(output)
        # If output indicates refinement is declined, refined_code_content will be None
        if not refined_code_content:
            return code

        refined_code_output = CodeOutput(
            kind=code.kind, filepath=code.filepath, content=refined_code_content
        )
        return refined_code_output

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        try:
            change_request = inputs["change_request"]
            implementation_plan = inputs["implementation_plan"]
            code = inputs["code"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")

        implementation_actions = ImplementationPlanParser.parse(implementation_plan)
        actions_by_filename = {
            action.filename: action for action in implementation_actions
        }
        code = CodeOutputParser.parse(code)
        rounds = inputs.get("rounds", 1)

        refined_code = []
        for code_output in code:
            for i in range(rounds):
                logger.debug(
                    "(refine-code) file: %s, round: %s", code_output.filepath, i
                )
                action = actions_by_filename[code_output.filepath]
                new_code_output = await self._refine_code(
                    role=context,
                    change_request=change_request,
                    code=code_output,
                    plan=action,
                )
                refined_code.append(new_code_output)

        final_refined_code_output = json.dumps(
            [code_output.dict() for code_output in refined_code]
        )
        self.store_output(final_refined_code_output)
        return {"refined_code": final_refined_code_output}

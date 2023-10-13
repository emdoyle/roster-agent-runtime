from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.common import TypedArgument

from ..parsers.xml import XMLTagContentParser
from ..util.llm import ask_openai
from .base import SYSTEM_PROMPT, BaseLocalAgentAction

logger = app_logger()

PROMPT_TEMPLATE = """
Role: {role}

## Instructions
Think step-by-step to break down the requested changes, and then figure out what to change in the current codebase.
Then, provide a list of files you would like to modify, abiding by the following:
* You may only create, modify, delete and rename files
* Including the FULL path, e.g. src/main.py and not just main.py, using the codebase tree below as the source of truth
* Prefer modifying existing files over creating new files
* Only modify or create files that DEFINITELY need to be touched
* Use detailed, natural language instructions on what to modify regarding business logic, and do not add low-level details like imports
* Do not modify non-text files such as images, svgs, binary, etc
* Follow the format example carefully, including step-by-step thoughts, a summary of the root cause, and the plan (enclosed in XML tags as shown)
-----
## Codebase tree
{codebase_tree}
-----
## Requested Changes
{change_request}
-----
## Format example
Step-by-step thoughts with explanations:
* Thought 1
* Thought 2
...

Plan Outline:
[Write an abstract, efficient plan to implement the requested changes. Try to determine the essence of the request. Be clear and concise.]

<plan>
<create file="file_path_1">
* Instruction 1 for file_path_1
* Instruction 2 for file_path_1
...
</create>

<create file="file_path_2">
* Instruction 1 for file_path_2
* Instruction 2 for file_path_2
...
</create>

...

<modify file="file_path_3">
* Instruction 1 for file_path_3
* Instruction 2 for file_path_3
...
</modify>

<modify file="file_path_4">
* Instruction 1 for file_path_4
* Instruction 2 for file_path_4
...
</modify>

...

<delete file="file_path_5"></delete>

...

<rename file="file_path_6">new full path for file path 6</rename>

...
</plan>
"""


class PlanCodeChanges(BaseLocalAgentAction):
    KEY = "PlanCodeChanges"
    SIGNATURE = (
        (
            TypedArgument.text("change_request"),
            TypedArgument.text("codebase_tree"),
        ),
        (TypedArgument.text("implementation_plan"),),
    )

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        try:
            change_request = inputs["change_request"]
            codebase_tree = inputs["codebase_tree"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")

        prompt = PROMPT_TEMPLATE.format(
            role=context, change_request=change_request, codebase_tree=codebase_tree
        )
        output = await ask_openai(prompt, SYSTEM_PROMPT)

        plan_content = XMLTagContentParser(tag="plan").parse(output)

        self.store_output(output)
        return {"implementation_plan": plan_content}

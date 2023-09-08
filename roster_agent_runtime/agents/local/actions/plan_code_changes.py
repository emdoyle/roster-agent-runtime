import os
import re

import openai
from roster_agent_runtime.agents.local.actions.base import (
    SYSTEM_PROMPT,
    LocalAgentAction,
)
from roster_agent_runtime.logs import app_logger

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
* Create/modify up to 5 FILES
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

Root cause:
[Write an abstract, efficient plan to address this issue in the least amount of change possible. Try to determine the root cause(s) of this issue. Be clear and concise. 1 paragraph.]

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


class DummyPlanCodeChanges(LocalAgentAction):
    KEY = "PlanCodeChanges"

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        return {
            "implementation_plan": """
<plan>
<modify file="roster_api/main.py">
* Add a nice comment to the top of the file ending with a smiley face
</modify>
</plan>
"""
        }


class PlanCodeChanges(LocalAgentAction):
    KEY = "PlanCodeChanges"

    output_regex = re.compile(r"(<plan>.*?</plan>)", re.DOTALL)

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        try:
            change_request = inputs["change_request"]
            codebase_tree = inputs["codebase_tree"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")
        system_message = {"content": SYSTEM_PROMPT, "role": "system"}
        prompt = PROMPT_TEMPLATE.format(
            role=context, change_request=change_request, codebase_tree=codebase_tree
        )
        user_message = {"content": prompt, "role": "user"}
        kwargs = {
            "api_key": os.environ["OPENAI_API_KEY"],
            "model": "gpt-4",
            "messages": [system_message, user_message],
            "n": 1,
            "stop": None,
            "temperature": 0.3,
        }
        logger.debug("(plan-code) input: %s", user_message)
        response = await openai.ChatCompletion.acreate(**kwargs)
        output = response.choices[0]["message"]["content"]

        with open("plan_code_changes_output.txt", "w") as f:
            f.write(output)
        logger.debug("(plan-code) output: %s", output)

        plan_match = output.search(self.output_regex)
        plan_xml_tree = plan_match.group(1) if plan_match else None

        return {"implementation_plan": plan_xml_tree}

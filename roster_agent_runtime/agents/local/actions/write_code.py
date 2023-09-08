import json
import os
import re
import xml.etree.ElementTree as ElementTree

import openai
from roster_agent_runtime.logs import app_logger

from .base import SYSTEM_PROMPT, LocalAgentAction

logger = app_logger()

CREATE_FILE_PROMPT_TEMPLATE = """
Role: {role}

## Instructions
Your task is to write the file: {filename} according to the implementation plan provided.
You can trust that the changes described in the implementation plan have already been implemented correctly,
aside from the changes that you should make to the current file.
Write code enclosed in an XML 'code' tag as shown in the Format example, keeping in mind the following rules and requirements.
* Implement the current file ONLY.
* The file must be syntactically valid. Do NOT add any content after the last line of code.
* Pay extremely close attention to the provided implementation plan.
* Think step by step before writing. Consider what needs to be implemented, and what your preferred design will be.
* Tip: CAREFULLY check that all references made in the file actually exist, and that you only use existing APIs.

-----
## Implementation Plan
{implementation_plan}
-----
## Format example
-----
## Code: {filename}
<code>
[your code here]
</code>"""

MODIFY_FILE_PROMPT_TEMPLATE = """
Role: {role}

## Instructions
You will be given the current contents of {filename}
Your task is to modify this file (if necessary) according to the implementation plan below.
You can trust that the changes described in the implementation plan have already been implemented correctly,
aside from the changes that you should make to the current file.
Write code enclosed in an XML 'code' tag as shown in the Format example, keeping in mind the following rules and requirements.
* Rewrite the entire contents of the file with your changes made directly.
* The file must be syntactically valid. Do NOT add any content after the last line of code.
* Pay extremely close attention to the provided implementation plan.
* Think step by step before writing. Consider what needs to be implemented, and what your preferred design will be.
* DO NOT attempt to refactor or fix any apparent design issues or bugs, UNLESS they directly inhibit your ability to follow the implementation plan.
* Tip: CAREFULLY check that all references made in the file actually exist, and that you only use existing APIs.

-----
## Implementation Plan
{implementation_plan}
-----
## Current contents of {filename}
{file_contents}
-----
## Format example
<code>
[your code here]
</code>
"""


def parse_implementation_plan(implementation_plan: str) -> list[dict]:
    implementation_actions = []
    try:
        root = ElementTree.fromstring(implementation_plan)
        for action in root:
            implementation_actions.append(
                {
                    "type": action.tag,
                    "filename": action.get("file"),
                    "plan": action.text.strip() if action.text else "",
                }
            )
    except ElementTree.ParseError as e:
        raise ValueError(f"Invalid implementation plan: {e}")
    return implementation_actions


class DummyWriteCode(LocalAgentAction):
    KEY = "WriteCode"

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        with open("code_output.txt", "r") as f:
            code = f.read()
            code_output = {
                "kind": "new_file",
                "filepath": "blackjack.py",
                "content": code,
            }
            return {"code": json.dumps(code_output)}


class WriteCode(LocalAgentAction):
    KEY = "WriteCode"

    output_regex = re.compile(r"(<code>.*?</code>)", re.DOTALL)

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        try:
            implementation_plan = inputs["implementation_plan"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")
        system_message = {"content": SYSTEM_PROMPT, "role": "system"}

        code_outputs = []
        implementation_actions = parse_implementation_plan(implementation_plan)
        for action in implementation_actions:
            if action["type"] == "create":
                prompt = CREATE_FILE_PROMPT_TEMPLATE.format(
                    role=context,
                    filename=action["filename"],
                    implementation_plan=implementation_plan,
                )
            elif action["type"] == "modify":
                # this part is actually not so clear!!
                # the workspace exists way on another machine
                # does this mean the agent needs to ask/wait for the contents via messaging?
                # does this mean the WorkflowRouter should parse the messages and embed content?
                # should there be a protected API to make this request to the API server directly?
                file_contents = ...
                prompt = MODIFY_FILE_PROMPT_TEMPLATE.format(
                    role=context,
                    filename=action["filename"],
                    implementation_plan=implementation_plan,
                    file_contents=file_contents,
                )
            elif action["type"] == "delete":
                code_outputs.append(
                    {
                        "kind": "delete_file",
                        "filepath": action["filename"],
                    }
                )
                continue
            else:
                raise ValueError(f"Invalid action type: {action['type']}")
            user_message = {"content": prompt, "role": "user"}
            kwargs = {
                "api_key": os.environ["OPENAI_API_KEY"],
                "model": "davinci",
                "messages": [system_message, user_message],
                "n": 1,
                "stop": None,
                "temperature": 0.3,
            }
            logger.debug("(write-code) input: %s", user_message)
            response = await openai.ChatCompletion.acreate(**kwargs)
            output = response.choices[0]["message"]["content"]
            logger.debug("(write-code) output: %s", output)

            code_match = output.search(self.output_regex)
            code_content = code_match.group(1) if code_match else None
            code_outputs.append(
                {
                    "kind": "new_file",
                    "filepath": action["filename"],
                    "content": code_content,
                }
            )

        with open("code_output.txt", "w") as f:
            f.write(json.dumps(code_outputs))

        return {"code": json.dumps(code_outputs)}

import json
import os

import openai
from roster_agent_runtime.logs import app_logger

from ..parsers.code import CodeOutput
from ..parsers.plan import ImplementationPlanParser
from ..parsers.xml import XMLTagContentParser
from .base import SYSTEM_PROMPT, BaseLocalAgentAction, LocalAgentAction

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


class DummyWriteCode(LocalAgentAction):
    KEY = "WriteCode"

    async def execute(
        self,
        inputs: dict[str, str],
        context: str = "",
    ) -> dict[str, str]:
        with open("code_output.txt", "r") as f:
            code = f.read()
            code_output = {
                "kind": "new_file",
                "filepath": "blackjack.py",
                "content": code,
            }
            return {"code": json.dumps(code_output)}


class WriteCode(BaseLocalAgentAction):
    KEY = "WriteCode"

    async def execute(
        self,
        inputs: dict[str, str],
        context: str = "",
    ) -> dict[str, str]:
        try:
            implementation_plan = inputs["implementation_plan"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")
        system_message = {"content": SYSTEM_PROMPT, "role": "system"}

        code_outputs = []
        implementation_actions = ImplementationPlanParser.parse(implementation_plan)
        modified_filenames = [
            action.filename
            for action in implementation_actions
            if action.type == "modify"
        ]
        # TODO: raise an error if message router isn't running/listening for Agent
        logger.debug("(write-code) About to read files: %s", modified_filenames)
        file_contents = await self.agent.read_files(
            filepaths=modified_filenames,
            record_id=self.record_id,
            workflow=self.workflow,
        )
        logger.debug("(write-code) Read files: %s", modified_filenames)
        file_contents = {
            file_content.filename: file_content for file_content in file_contents
        }

        for action in implementation_actions:
            if action.type == "create":
                prompt = CREATE_FILE_PROMPT_TEMPLATE.format(
                    role=context,
                    filename=action.filename,
                    implementation_plan=implementation_plan,
                )
            elif action.type == "modify":
                current_file_content = file_contents[action.filename]
                prompt = MODIFY_FILE_PROMPT_TEMPLATE.format(
                    role=context,
                    filename=action.filename,
                    implementation_plan=implementation_plan,
                    file_contents=current_file_content,
                )
            elif action.type == "delete":
                code_outputs.append(
                    CodeOutput(kind="delete_file", filepath=action.filename)
                )
                continue
            else:
                raise ValueError(f"Invalid action type: {action.type}")
            user_message = {"content": prompt, "role": "user"}
            kwargs = {
                "api_key": os.environ["ROSTER_OPENAI_API_KEY"],
                "model": "gpt-4",
                "messages": [system_message, user_message],
                "n": 1,
                "stop": None,
                "temperature": 0.3,
            }
            logger.debug("(write-code) input: %s", user_message)
            response = await openai.ChatCompletion.acreate(**kwargs)
            output = response.choices[0]["message"]["content"]
            logger.debug("(write-code) output: %s", output)

            code_content = XMLTagContentParser(tag="code").parse(
                output, inclusive=False
            )
            code_outputs.append(
                CodeOutput(
                    kind="new_file", filepath=action.filename, content=code_content
                )
            )

        final_code_output = json.dumps(
            [code_output.dict() for code_output in code_outputs]
        )
        self.store_output(final_code_output)
        return {"code": final_code_output}

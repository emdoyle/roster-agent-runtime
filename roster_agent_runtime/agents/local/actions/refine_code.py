import json
import os

import openai
from roster_agent_runtime.logs import app_logger

from .base import SYSTEM_PROMPT, LocalAgentAction

logger = app_logger()


PROMPT_TEMPLATE = """
Role: {role}

## Instructions
Modify the given code to ensure that it meets the requirements faithfully.
Make minimal changes when possible, and prefer to introduce a new abstraction ONLY when it can significantly reduce the complexity of the code.
It is possible that the given code fails to satisfy some of the requirements. In such cases, you MUST modify the code to satisfy as many of the requirements as possible.
If all requirements appear to be satisfied, make minimal changes (comments, formatting etc.) to the code to ensure that it is syntactically valid.
1. Requirement: Modify the current file ONLY.
2. Requirement: The file must be syntactically valid. Do NOT add any content after the last line of code.
3. Requirement: Pay extremely close attention to the provided requirements document, and satisfy as many of the requirements as possible.
4. Tip: Think before writing. You may include some deliberation and planning in your response, as long as it comes before the formatted code block. Consider what needs to be implemented, and what your preferred design will be.
5. Tip: CAREFULLY check that all references made in the file actually exist, and that you only use existing APIs.

-----
## Requirements
{requirements}
-----
## Original Code
{original_code}
-----

## Format example
-----
## Code: {filename}
```python
# {filename}
<your code here>
```
"""


class DummyRefineCode(LocalAgentAction):
    KEY = "RefineCode"

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        return {"refined_code": inputs["code"]}


class RefineCode(LocalAgentAction):
    KEY = "RefineCode"

    async def _refine_code(
        self, role: str, requirements: str, code: str, filename: str = "main.py"
    ):
        system_message = {"content": SYSTEM_PROMPT, "role": "system"}
        prompt = PROMPT_TEMPLATE.format(
            role=role,
            requirements=requirements,
            original_code=code,
            filename=filename,
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
        logger.debug("(refine-code) input: %s", user_message)
        response = await openai.ChatCompletion.acreate(**kwargs)
        output = response.choices[0]["message"]["content"]
        logger.debug("(refine-code) output: %s", output)
        return output

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        try:
            requirements = inputs["requirements_document"]
            code = inputs["code"]
            codebase_tree = inputs["codebase_tree"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")

        rounds = inputs.get("rounds", 1)
        for i in range(rounds):
            logger.debug("(refine-code) round: %s", i)
            code = await self._refine_code(
                role=context, requirements=requirements, code=code
            )
            with open(f"refined_code_output_{i}.txt", "w") as f:
                f.write(code)

        python_code = code.split("```python")[1].split("```")[0].strip()
        code_output = {
            "kind": "new_file",
            "filepath": "main.py",
            "content": python_code,
        }
        return {"refined_code": json.dumps(code_output)}

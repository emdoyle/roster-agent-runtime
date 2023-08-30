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


class RefineCode(LocalAgentAction):
    KEY = "RefineCode"

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        try:
            requirements = inputs["requirements_document"]
            code = inputs["code"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")
        system_message = {"content": SYSTEM_PROMPT, "role": "system"}
        prompt = PROMPT_TEMPLATE.format(
            role=context,
            requirements=requirements,
            original_code=code,
            filename="main.py",
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
        logger.debug("(refine-code) kwargs: %s", kwargs)
        response = await openai.ChatCompletion.acreate(**kwargs)
        output = response.choices[0]["message"]["content"]
        with open("refined_code_output.txt", "w") as f:
            f.write(output)
        logger.debug("(refine-code) output: %s", output)

        return {"refined_code": output}

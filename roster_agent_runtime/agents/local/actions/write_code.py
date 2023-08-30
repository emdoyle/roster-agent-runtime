import os

import openai
from roster_agent_runtime.logs import app_logger

from .base import SYSTEM_PROMPT, LocalAgentAction

logger = app_logger()

PROMPT_TEMPLATE = """
Role: {role}

## Instructions
Write code enclosed in triple backticks, keeping in mind the following rules and requirements.
1. Requirement: Implement the current file ONLY.
2. Requirement: The file must be syntactically valid. Do NOT add any content after the last line of code.
3. Requirement: Pay extremely close attention to the provided requirements document, and implement the requirements as well as you can.
4. Tip: Think before writing. Consider what needs to be implemented, and what your preferred design will be.
5. Tip: CAREFULLY check that all references made in the file actually exist, and that you only use existing APIs.

-----
## Requirements
{requirements}
-----
## Format example
-----
## Code: {filename}
```python
# {filename}
<your code here>
```"""


class WriteCode(LocalAgentAction):
    KEY = "WriteCode"

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        try:
            requirements = inputs["requirements_document"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")
        system_message = {"content": SYSTEM_PROMPT, "role": "system"}
        prompt = PROMPT_TEMPLATE.format(
            role=context, requirements=requirements, filename="main.py"
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
        logger.debug("(write-code) kwargs: %s", kwargs)
        response = await openai.ChatCompletion.acreate(**kwargs)
        output = response.choices[0]["message"]["content"]
        with open("code_output.txt", "w") as f:
            f.write(output)
        logger.debug("(write-code) output: %s", output)

        return {"code": output}

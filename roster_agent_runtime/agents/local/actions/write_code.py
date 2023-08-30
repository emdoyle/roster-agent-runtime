import os

import openai
from roster_agent_runtime.agents.local.actions.base import LocalAgentAction
from roster_agent_runtime.logs import app_logger

logger = app_logger()

# TODO: where does this live?
SYSTEM_PROMPT = """This conversation is happening within a system called Roster,
and you are acting as an Agent in this system. The User is a human being who is
operating the system and is trying to accomplish a task. The User will provide
guidance on your role in the system, and describe the task at hand. You will
perform the task to the best of your ability, paying close attention to all instructions."""

PROMPT_TEMPLATE = """
NOTICE
Role: {role}
ATTENTION: Use '##' to split sections, not '#'. Follow the 'Format example' carefully when providing your response.

## Instructions
Write code enclosed in triple backticks, keeping in mind the following rules and requirements.
1. Requirement: Implement the current file ONLY.
2. Requirement: The file must be syntactically valid. Do NOT add any content after the last line of code.
3. Tip: Think before writing. Consider what needs to be implemented, and what your preferred design will be.
4. Tip: CAREFULLY check that all references made in the file actually exist, and that you only use existing APIs.

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
```
-----
"""


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
        logger.debug("(write-code) response: %s", response)

        return {"code": response.choices[0]["message"]["content"]}

import os

import openai
from roster_agent_runtime.logs import app_logger

from .base import SYSTEM_PROMPT, BaseLocalAgentAction, LocalAgentAction

logger = app_logger()

PROMPT_TEMPLATE = """
Role: {role}
ATTENTION: Use '###' to split sections in your response. Follow the 'Format example' carefully when providing your response.

## Instructions
Distill the user's requests (from the section titled 'User Requests' below) into clear, orthogonal product goals and user stories.
If the requirements are unclear, ensure minimum viability and avoid excessive requirements.
Your response should include the following sections:
### Product Goals: Provided as Python list[str], up to 3 clear, orthogonal product goals based on the user's requests. If the request itself is simple, the goal(s) should also be simple.
### Requirement Analysis: Provide as Plain text. Discuss the high-level requirements or boundaries implied by the user's requests and your product goals. Be concise.
### Requirement Pool: Provided as Python list[tuple[str, str]], the tuple contains a requirement description and a priority level (P0/P1/P2), respectively. These should be clear and direct requirements derived from your analysis above along with the user's requests and your product goals. A software engineer should be able to easily understand their intent.


## User Requests
{user_requests}
-----

## Format example
{format_example}
-----
"""

FORMAT_EXAMPLE = """
### Product Goals
```python
[
    "Create a ...",
]
```

### Requirement Analysis
The product should be a ...

### Requirement Pool
```python
[
    ("End game when ...", "P0")
]
```
"""


class DummyWritePRD(LocalAgentAction):
    KEY = "DistillFeatureRequirements"

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        return {"requirements_document": "Do whatever you want"}


class WritePRD(BaseLocalAgentAction):
    KEY = "DistillFeatureRequirements"
    SIGNATURE = (
        ({"type": "text", "name": "customer_requests"},),
        ({"type": "text", "name": "requirements_document"},),
    )

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        try:
            user_requests = inputs["customer_requests"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")
        system_message = {"content": SYSTEM_PROMPT, "role": "system"}
        prompt = PROMPT_TEMPLATE.format(
            role=context, user_requests=user_requests, format_example=FORMAT_EXAMPLE
        )
        user_message = {"content": prompt, "role": "user"}
        kwargs = {
            "api_key": os.environ["ROSTER_OPENAI_API_KEY"],
            "model": "gpt-4",
            "messages": [system_message, user_message],
            "n": 1,
            "stop": None,
            "temperature": 0.3,
        }
        logger.debug("(write-prd) input: %s", user_message)
        response = await openai.ChatCompletion.acreate(**kwargs)
        output = response.choices[0]["message"]["content"]
        logger.debug("(write-prd) output: %s", output)

        self.store_output(output)
        return {"requirements_document": output}

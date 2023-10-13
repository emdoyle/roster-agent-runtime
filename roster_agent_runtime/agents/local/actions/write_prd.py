from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.common import TypedArgument

from ..util.llm import ask_openai
from .base import SYSTEM_PROMPT, BaseLocalAgentAction

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


class WritePRD(BaseLocalAgentAction):
    KEY = "DistillFeatureRequirements"
    SIGNATURE = (
        (TypedArgument.text("customer_requests"),),
        (TypedArgument.text("requirements_document"),),
    )

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        try:
            user_requests = inputs["customer_requests"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")
        prompt = PROMPT_TEMPLATE.format(
            role=context, user_requests=user_requests, format_example=FORMAT_EXAMPLE
        )
        output = await ask_openai(prompt, SYSTEM_PROMPT)

        self.store_output(output)
        return {"requirements_document": output}

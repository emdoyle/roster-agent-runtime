from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.common import TypedArgument

from ..util.llm import ask_openai
from .base import SYSTEM_PROMPT, BaseLocalAgentAction

logger = app_logger()


EXTRACT_ENTITIES_TEMPLATE = """
Role: {role}

## Instructions
I want to identify distinct domains within a software project.
To do this, your current task is to identify the most significant entities (functions, classes, files or directories) which define the architecture of the project.
You will receive a simple natural language description of the project.
You will also be provided with the entire directory structure of the project, as well as some information about the entities in each file.
To complete the task you should produce a list of the most significant entities (from the codebase tree) according to the Format example below.
Keep in mind the following while you do this:
* The chosen entities should be the ones which are MOST important when considering how to maintain and extend the software
* Prefer to choose wider-scope entities (directories > files > classes > functions) when their members would themselves be significant entities
* These entities will be divided amongst Experts, ensure that each entity represents a coherent role or responsibility in the project
* Think step by step before making your selections.

-----
## Project Description
{project_description}
-----
## Codebase Tree
{codebase_tree}
-----
## Format example
-----
## Entities
<entity function="filepath:function">
[description of the significance of this function]
</entity>
<entity class="filepath:class">
[description of the significance of this class]
</entity>
<entity file="filepath">
[description of the significance of this file]
</entity>
<entity dir="directory">
[description of the significance of this directory]
</entity>"""


class IdentifyDomains(BaseLocalAgentAction):
    KEY = "IdentifyDomains"
    SIGNATURE = (
        (
            TypedArgument.text("project_description"),
            TypedArgument.text("codebase_tree"),
        ),
        (TypedArgument.text("domains"),),
    )

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        try:
            project_description = inputs["project_description"]
            codebase_tree = inputs["codebase_tree"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")

        prompt = EXTRACT_ENTITIES_TEMPLATE.format(
            role=context,
            project_description=project_description,
            codebase_tree=codebase_tree,
        )
        response = await ask_openai(prompt, SYSTEM_PROMPT)

        self.store_output(response)
        return {"domains": response}

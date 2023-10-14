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


CLUSTER_EXPERTS_PROMPT = """
Role: {role}

## Instructions
Your current task is to divide responsibility for parts of a software project across Experts.
You will receive a simple natural language description of the project.
You will also be provided with the a list of the most significant entities in the project.
You should produce a list of Experts according to the Format example below.
Keep in mind the following while you do this:
* Each Expert should be responsible for a set of entities which could be seen as having something in common
* Prefer to assign entities which belong to a common semantic 'layer' to a single Expert
* Prefer to split responsibilities such that Experts have similar amounts of code to manage when possible
* All entities should be assigned to AT LEAST ONE Expert, and in exceptional cases may be assigned to more than one Expert (prefer not to do this)
* A 'miscellaneous' Expert can be used to group several small, peripheral responsibilities when necessary
* Think step by step before making your selections.

-----
## Project Description
{project_description}
-----
## Entities
{entities}
-----
## Format example
<expert name="Expert Name">
<description>
[high-level description of the responsibility of this Expert]
</description>
<entity dir="directory" />
<entity class="filepath:class" />
<entity class="filepath:class" />
</expert>
<expert name="Expert Name">
<description>
[high-level description of the responsibility of this Expert]
</description>
<entity class="filepath:class" />
<entity function="filepath:function" />
<entity file="filepath" />
</expert>
"""


class SuggestExperts(BaseLocalAgentAction):
    KEY = "SuggestExperts"
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

        entity_prompt = EXTRACT_ENTITIES_TEMPLATE.format(
            role=context,
            project_description=project_description,
            codebase_tree=codebase_tree,
        )
        entity_response = await ask_openai(entity_prompt, SYSTEM_PROMPT)
        # TODO: might want to parse entities, remove overlaps (although overlaps may be significant?)

        expert_prompt = CLUSTER_EXPERTS_PROMPT.format(
            role=context,
            project_description=project_description,
            entities=entity_response,
        )
        expert_response = await ask_openai(expert_prompt, SYSTEM_PROMPT)

        self.store_output(entity_response + "\n" + expert_response)
        return {"experts": expert_response}

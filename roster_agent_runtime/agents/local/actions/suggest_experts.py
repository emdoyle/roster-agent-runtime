from itertools import chain

from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.common import TypedArgument

from ..parsers.codebase_tree import CodebaseTreeParser
from ..parsers.experts import ExpertsParser
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
* List chosen entities with wider-scoped entities first (directories > files > classes > functions)
* DO NOT choose an entity which is already included by a wider-scoped entity
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
<entity dir="directory">
[description of the significance of this directory]
</entity>
<entity file="filepath">
[description of the significance of this file]
</entity>
<entity class="filepath:class">
[description of the significance of this class]
</entity>
<entity function="filepath:function">
[description of the significance of this function]
</entity>
"""


CLUSTER_EXPERTS_PROMPT = """
Role: {role}

## Instructions
Your current task is to divide responsibility for parts of a software project across Experts.
You will receive a simple natural language description of the project.
You will also be provided with a list of the most significant entities in the project.
You should produce a list of Experts according to the Format example below.
Keep in mind the following while you do this:
* Each Expert should be responsible for a set of entities which could be seen as having something in common
* Prefer to split responsibilities such that Experts have similar amounts of code to manage when possible
* A single Expert should not be responsible for overlapping entities
* If an Expert is responsible for an entity which includes others (like when a directory includes a file etc.), the lower-level/included entities do not need to be assigned
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

REMAINING_EXPERTS_PROMPT = """
Role: {role}

## Instructions
Your current task is to divide responsibility for parts of a software project across Experts.
Most of the software project has already been assigned to various Experts, but there are some files remaining which need to be assigned.
You will receive a simple natural language description of the project.
You will also receive a tree of the remaining unassigned portions of the codebase, as well as a list of the already-assigned Experts.
You should produce a list of additional Experts according to the Format example below.
Keep in mind the following while you do this:
* Do not repeat any Experts or entities which appear under 'Experts Already Assigned'
* Each Expert should be responsible for a set of entities which could be seen as having something in common
* Prefer to split responsibilities such that Experts have similar amounts of code to manage when possible
* A single Expert should not be responsible for overlapping entities
* If an Expert is responsible for an entity which includes others (like when a directory includes a file etc.), the lower-level/included entities do not need to be assigned
* Think step by step before making your selections.

-----
## Project Description
{project_description}
-----
## Unassigned Portion of the Codebase Tree
{codebase_tree}
-----
## Experts Already Assigned
{experts}
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
        (TypedArgument.text("experts"),),
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
        #   for now, overlaps are handled by LLM which is probably error-prone
        expert_prompt = CLUSTER_EXPERTS_PROMPT.format(
            role=context,
            project_description=project_description,
            entities=entity_response,
        )
        expert_response = await ask_openai(expert_prompt, SYSTEM_PROMPT)

        parsed_experts = ExpertsParser.parse(expert_response)
        parsed_tree = CodebaseTreeParser.parse(codebase_tree)
        unassigned_tree = parsed_tree.remaining_tree(
            list(chain(*(expert.entities for expert in parsed_experts)))
        )

        remaining_experts_prompt = REMAINING_EXPERTS_PROMPT.format(
            role=context,
            project_description=project_description,
            experts=expert_response,
            codebase_tree=unassigned_tree.display(),
        )
        remaining_experts_response = await ask_openai(
            remaining_experts_prompt, SYSTEM_PROMPT
        )

        # parse new experts, combine them, check for any remaining entities
        # throw new entities (files, dirs) into a 'leftover' Expert
        # do a final dedupe/cleaning pass

        self.store_output(
            entity_response + "\n" + expert_response + "\n" + remaining_experts_response
        )
        return {"experts": expert_response + "\n" + remaining_experts_response}

from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.common import TypedArgument
from scripts.util import CFN_GITHUB_PR_FILE, CFN_WORKFLOW_INIT_FILE

from ..parsers.codebase_tree import CodebaseTreeParser
from ..parsers.xml import XMLTagContentParser
from ..util.llm import ask_openai
from .base import SYSTEM_PROMPT, BaseLocalAgentAction

logger = app_logger()

PLAN_INSTRUCTIONS_TEMPLATE = """
Role: {role}

## Instructions
You are managing a team of Experts, each responsible for their own part of the codebase shown below.
Your task is to understand the Requested Changes provided below, and to give high-level instructions to each relevant Expert in order to implement the changes according to the Format Example.
You will be provided with a broad, global summary of the project, as well as the directory structure of the codebase.
You may also be provided with relevant 'narratives', each of which explains how a single high-level objective is implemented by multiple files in sequence. 
Keep in mind the following while you prepare your plan:
* You are not responsible for deciding exactly which files will be changed, but your instructions should be appropriate for the focus of each Expert
* Your instructions should explain to the associated Expert what functionality they must change, remove, or introduce
* The Expert will receive general information about the project and may see relevant narratives, but will NOT see instructions given to the rest of the Experts. Ensure that each Expert's instructions are interpretable on their own.
* You should mention in your instructions whenever an Expert should wait for the changes made by another Expert by using the 'dependency' tag as shown in the Format Example
* Translate the requested changes into potential changes in the project by thinking step-by-step
* Prefer to use as few Experts as possible, and to keep your requested changes as simple as possible

-----
## Project Summary
{project_summary}
-----
## Codebase Paths
{codebase_paths}
-----
## Experts
{experts}
-----
## Useful Narratives
{narratives}
-----
## Requested Changes
{change_request}
-----
## Format example
Step-by-step thoughts with explanations:
* Thought 1
* Thought 2
...

<plan>
<expert name="Expert name">
<instructions>
[instructions for the Expert]
</instructions>
<dependency name="Other Expert name OR 'leftover'">
[explanation of how this Expert's work may depend on Other Expert's work]
</collab>
</expert>
...
<leftover>
[instructions for changes required to files NOT managed by any Expert]
</leftover>
</plan>
"""


class PlanCodeChanges(BaseLocalAgentAction):
    KEY = "PlanCodeChanges"
    SIGNATURE = (
        (
            TypedArgument.text("change_request"),
            TypedArgument.text("project_summary"),
            TypedArgument.text("experts"),
            TypedArgument.text("codebase_tree"),
        ),
        (TypedArgument.text("expert_instructions"),),
    )

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        try:
            change_request = inputs["change_request"]
            project_summary = inputs["project_summary"]
            experts = inputs["experts"]
            codebase_tree = inputs["codebase_tree"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")

        parsed_tree = CodebaseTreeParser.parse(codebase_tree)

        # TODO: this is temporary pending real CFN search
        narratives = []
        with open(CFN_GITHUB_PR_FILE, "r") as f:
            narratives.append(f.read())
        with open(CFN_WORKFLOW_INIT_FILE, "r") as f:
            narratives.append(f.read())

        prompt = PLAN_INSTRUCTIONS_TEMPLATE.format(
            role=context,
            project_summary=project_summary,
            codebase_paths="\n".join(parsed_tree.entities_by_file.keys()),
            experts=experts,
            change_request=change_request,
            narratives="\n\n".join(narratives),
        )
        output = await ask_openai(prompt, SYSTEM_PROMPT)
        plan_content = XMLTagContentParser(tag="plan").parse(output)

        self.store_output(output)
        return {"expert_instructions": plan_content}

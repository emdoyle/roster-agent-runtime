from roster_agent_runtime.agents.local.actions.base import SYSTEM_PROMPT
from roster_agent_runtime.agents.local.parsers.codebase_tree import CodebaseTree
from roster_agent_runtime.agents.local.parsers.plan import (
    ExpertInstructions,
    ImplementationPlanAction,
    ImplementationPlanParser,
)
from roster_agent_runtime.agents.local.parsers.xml import XMLTagContentParser
from roster_agent_runtime.agents.local.util.llm import ask_openai
from scripts.util import CFN_GITHUB_PR_EXPANDED_FILE, CFN_WORKFLOW_INIT_EXPANDED_FILE

EXPERT_PLAN_TEMPLATE = """
Role: {role}

## Instructions
You are an Expert responsible for a specific portion of this project's codebase.
You will be provided with a summary of the project.
You will also be provided with the original Requested Changes from the User, and the specific Instructions from your Manager to guide you.
In the codebase tree, you will see the directory structure of the files you are responsible for, along with notable entities within them.
You may see relevant 'narratives' from the project, each of which explains how a single high-level objective is implemented by multiple files in sequence.
You may also see the changes that other Experts have already made, based on their own Instructions. Pay attention to see if their changes affect your own, and do not make changes in conflict with what they have already done.
Think step-by-step to break down the requested changes, and then figure out what changes you will need to make in your portion of the codebase.
Then, provide a list of actions you will take according to the Format Example.
Keep in mind the following:
* You may only take actions on paths in YOUR portion of the codebase as shown in the codebase tree
* Including the FULL path, e.g. src/main.py and not just main.py, using the codebase tree below as the source of truth
* Prefer modifying existing files over creating new files
* Think step-by-step before deciding which actions you will take
-----
## Project Summary
{project_summary}
-----
## Requested Changes
{change_request}
-----
## Instructions
{instructions}
-----
## Codebase tree
{codebase_tree}
-----
## Narratives
{narratives}
-----
## Format example
Step-by-step thoughts with explanations:
* Thought 1
* Thought 2
...

<plan>
<modify file="file_path_1">
* Instruction 1 for file_path_1
* Instruction 2 for file_path_1
...
</modify>
<create file="file_path_2">
* Instruction 1 for file_path_2
* Instruction 2 for file_path_2
...
</create>
<delete file="file_path_5" />
<rename file="file_path_6" newPath="new_path_6" />
</plan>
"""


async def generate_expert_implementation_plan(
    project_summary: str,
    change_request: str,
    instructions: ExpertInstructions,
    codebase_tree: CodebaseTree,
    context: str = "",
) -> list[ImplementationPlanAction]:
    expanded_narratives = []
    with open(CFN_GITHUB_PR_EXPANDED_FILE, "r") as f:
        expanded_narratives.append(f.read())
    with open(CFN_WORKFLOW_INIT_EXPANDED_FILE, "r") as f:
        expanded_narratives.append(f.read())

    prompt = EXPERT_PLAN_TEMPLATE.format(
        role=context,
        project_summary=project_summary,
        change_request=change_request,
        instructions=instructions.text,
        codebase_tree=codebase_tree.display(),
        narratives="\n\n".join(expanded_narratives),
    )
    plan_response = await ask_openai(prompt, SYSTEM_PROMPT)
    with open(
        f"/Users/evanmdoyle/Programming/roster-agent-runtime/action_outputs/WriteCode/fake-test-{instructions.name}.txt",
        "w",
    ) as f:
        f.write(prompt + "\n\n------------------\n\n" + plan_response)
    plan_content = XMLTagContentParser(tag="plan").parse(plan_response)

    return ImplementationPlanParser.parse(plan_content)

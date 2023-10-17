from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.common import TypedArgument
from scripts.util import CFN_GITHUB_PR_EXPANDED_FILE, CFN_GITHUB_PR_FILE

from ..parsers.codebase_tree import CodebaseTreeParser
from ..parsers.xml import XMLTagContentParser
from ..util.llm import ask_openai
from .base import SYSTEM_PROMPT, BaseLocalAgentAction

logger = app_logger()

# showing relevant snippets in the order in which they would be invoked

PLAN_INSTRUCTIONS_TEMPLATE = """
Role: {role}

## Instructions
You are managing a team of Experts, each responsible for their own part of the codebase shown below.
Not all files are managed by an Expert, these are typically less significant to the project and can be managed by a generalist.
In order to more effectively maintain and extend the code, your Experts have read their associated code and prepared summaries.
You will be provided with their summaries, along with a broader, global summary of the project.
You will also be provided with a relevant 'narrative', which explains how a single high-level objective is implemented by multiple files in sequence. 
Your task is now to understand the Requested Changes provided below, and to give high-level instructions to each relevant Expert in order to implement the changes.
Keep in mind the following while you do this:
* You are not responsible for deciding exactly which files will be changed, but your instructions should be appropriate for the focus of each Expert
* Your instructions should explain to the associated Expert what functionality they must change, remove, or introduce
* You should mention in your instructions whenever an Expert should wait for the changes made by another Expert (e.g. function/class interface changes, name changes etc.) by using the 'dependency' tag as shown in the Format Example
* If changes are required in files which are NOT managed by any Expert, include all of these in the 'leftover' tag as shown in the Format Example
* Translate the requested changes into potential changes in the project by thinking step-by-step
* Prefer to use as few Experts as possible, and to keep your requested changes as simple as possible

-----
## Project Summary
{project_summary}
-----
## Codebase Paths
{codebase_paths}
-----
## Expert Summaries
{expert_summaries}
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

PROMPT_TEMPLATE = """
Role: {role}

## Instructions
Think step-by-step to break down the requested changes, and then figure out what to change in the current codebase.
Then, provide a list of files you would like to modify, abiding by the following:
* You may only create, modify, delete and rename files
* Including the FULL path, e.g. src/main.py and not just main.py, using the codebase tree below as the source of truth
* Prefer modifying existing files over creating new files
* Only modify or create files that DEFINITELY need to be touched
* Use detailed, natural language instructions on what to modify regarding business logic, and do not add low-level details like imports
* Do not modify non-text files such as images, svgs, binary, etc
* Follow the format example carefully, including step-by-step thoughts, a summary of the root cause, and the plan (enclosed in XML tags as shown)
-----
## Codebase tree
{codebase_tree}
-----
## Requested Changes
{change_request}
-----
## Format example
Step-by-step thoughts with explanations:
* Thought 1
* Thought 2
...

Plan Outline:
[Write an abstract, efficient plan to implement the requested changes. Try to determine the essence of the request. Be clear and concise.]

<plan>
<create file="file_path_1">
* Instruction 1 for file_path_1
* Instruction 2 for file_path_1
...
</create>

<create file="file_path_2">
* Instruction 1 for file_path_2
* Instruction 2 for file_path_2
...
</create>

...

<modify file="file_path_3">
* Instruction 1 for file_path_3
* Instruction 2 for file_path_3
...
</modify>

<modify file="file_path_4">
* Instruction 1 for file_path_4
* Instruction 2 for file_path_4
...
</modify>

...

<delete file="file_path_5"></delete>

...

<rename file="file_path_6">new full path for file path 6</rename>

...
</plan>
"""


class PlanCodeChanges(BaseLocalAgentAction):
    KEY = "PlanCodeChanges"
    SIGNATURE = (
        (
            TypedArgument.text("change_request"),
            TypedArgument.text("project_summary"),
            TypedArgument.text("expert_summaries"),
            TypedArgument.text("codebase_tree"),
        ),
        (TypedArgument.text("implementation_plan"),),
    )

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        try:
            project_summary = inputs["project_summary"]
            expert_summaries = inputs["expert_summaries"]
            change_request = inputs["change_request"]
            codebase_tree = inputs["codebase_tree"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")

        parsed_tree = CodebaseTreeParser.parse(codebase_tree)

        with open(CFN_GITHUB_PR_FILE, "r") as f:
            narratives = f.read()

        prompt = PLAN_INSTRUCTIONS_TEMPLATE.format(
            role=context,
            project_summary=project_summary,
            codebase_paths="\n".join(parsed_tree.entities_by_file.keys()),
            expert_summaries=expert_summaries,
            change_request=change_request,
            narratives=narratives,
        )
        output = await ask_openai(prompt, SYSTEM_PROMPT)

        plan_content = XMLTagContentParser(tag="plan").parse(output)

        self.store_output(output)
        return {"implementation_plan": plan_content}

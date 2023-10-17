from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.common import TypedArgument

from ..parsers.codebase_tree import CodebaseTreeParser
from ..parsers.experts import ExpertsParser
from ..parsers.xml import XMLTagContentParser
from ..util.llm import ask_openai
from .base import SYSTEM_PROMPT, BaseLocalAgentAction

logger = app_logger()


SUMMARIZE_FILE_PROMPT = """
Role: {role}

## Instructions
You are the designated Expert responsible for managing the entities listed below.
In order to more effectively maintain and extend the code related to these entities, you will read the associated code and summarize it.
You will receive a simple natural language description of the project.
You will also be provided with a subset of the directory structure of the project which includes your managed entities.
Most importantly, you will receive the contents of one of the files from this directory structure.
Your task is to summarize these contents at a high-level.
Keep in mind the following while you do this:
* Your summary should aim to answer the questions: what is the code responsible for, and how does it satisfy its responsibilities?
* Your summary will eventually be used to aid in planning changes to the code, so it must help a prospective maintainer understand the underlying theory and intention of the code whenever possible
* Your summary should make sure to pay specific attention to the Entities mentioned below if they appear in the file contents
* Think step-by-step when writing your summary

-----
## Project Description
{project_description}
-----
## Entities
{entities}
-----
## Codebase Tree
{codebase_tree}
-----
## File: {filename}
{file_contents}
-----
## Format example
<summary>
[your summary of the file]
</summary>
"""
EXPERT_SUMMARY_PROMPT = """
Role: {role}

## Instructions
You are the designated Expert responsible for managing the codebase tree shown below.
This is a subset of a larger project.
In order to more effectively maintain and extend the code, you have read the associated code and summarized it.
You will be provided with your summaries.
Your task is now to condense these summaries into a higher-level picture of how the entities fit together.
Keep in mind the following while you do this:
* Your summary should aim to answer the questions: how do these files relate to each other, and how do they satisfy their responsibilities?
* Your summary will eventually be used to aid in planning changes to the code, so it must help a prospective maintainer understand the underlying theory and intention of the code whenever possible
* Think step-by-step when writing your summary

-----
## Project Description
{project_description}
-----
## Codebase Tree
{codebase_tree}
-----
## File Summaries
{file_summaries}
-----
## Format example
<summary>
[your broad summary]
</summary>
"""

FINAL_SUMMARY_PROMPT = """
Role: {role}

## Instructions
You are managing a team of Experts, each responsible for their own part of the codebase shown below.
Not all files are managed by an Expert, these are typically less significant to the project and can be managed by a generalist.
In order to more effectively maintain and extend the code, your Experts have read their associated code and prepared summaries.
You will be provided with their summaries.
Your task is now to condense these summaries into a higher-level picture of how the project is implemented.
Keep in mind the following while you do this:
* Your summary should aim to answer the questions: how is this project organized, and how does it accomplish its goals?
* Your summary will eventually be used to aid in planning changes to the code, so it must help a prospective maintainer understand the underlying theory of the project whenever possible
* Think step-by-step when writing your summary

-----
## Project Description
{project_description}
-----
## Codebase Paths
{codebase_paths}
-----
## Expert Summaries
{expert_summaries}
-----
## Format example
<finalSummary>
[your final summary]
</finalSummary>
"""


class SummarizeCodebase(BaseLocalAgentAction):
    KEY = "SummarizeCodebase"
    SIGNATURE = (
        (
            TypedArgument.text("project_description"),
            TypedArgument.text("codebase_tree"),
            TypedArgument.text("experts"),
        ),
        (TypedArgument.text("summary"),),
    )

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        # temp: allows collecting outputs to store in file record
        outputs = []

        try:
            project_description = inputs["project_description"]
            codebase_tree = inputs["codebase_tree"]
            experts = inputs["experts"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")

        parsed_tree = CodebaseTreeParser.parse(codebase_tree)
        parsed_experts = ExpertsParser.parse(experts)

        expert_summaries: list[str] = []
        # temp: hack for ensuring outputs are collected
        final_summary = ""

        # temp: for ensuring outputs are collected
        try:
            for expert in parsed_experts:
                summaries_by_file: dict[str, str] = {}
                filtered_tree = parsed_tree.filtered_tree(expert.entities)
                entities_display = "\n".join(
                    (entity.display() for entity in expert.entities)
                )
                filepaths = list(filtered_tree.entities_by_file.keys())
                file_contents = await self.agent.read_files(
                    filepaths=filepaths,
                    record_id=self.record_id,
                    workflow=self.workflow,
                )

                for file_content in file_contents:
                    summarize_prompt = SUMMARIZE_FILE_PROMPT.format(
                        role=context,
                        project_description=project_description,
                        entities=entities_display,
                        codebase_tree=filtered_tree.display(),
                        filename=file_content.filename,
                        file_contents=file_content.text,
                    )
                    summarize_response = await ask_openai(
                        summarize_prompt, SYSTEM_PROMPT
                    )
                    summary = XMLTagContentParser(tag="summary").parse(
                        summarize_response, inclusive=False
                    )
                    summaries_by_file[file_content.filename] = summary

                file_summaries_display = "\n".join(
                    (
                        f'<fileSummary file="{filename}">\n{file_summary}\n</fileSummary>'
                        for filename, file_summary in summaries_by_file.items()
                    )
                )
                expert_summary_prompt = EXPERT_SUMMARY_PROMPT.format(
                    role=context,
                    project_description=project_description,
                    codebase_tree=filtered_tree.display(),
                    file_summaries=file_summaries_display,
                )
                expert_summary_response = await ask_openai(
                    expert_summary_prompt, SYSTEM_PROMPT
                )
                expert_summary = XMLTagContentParser(tag="summary").parse(
                    expert_summary_response, inclusive=False
                )
                expert_summaries.append(
                    f'<expert name="{expert.name}">\n{entities_display}\n<summary>\n{expert_summary}\n</summary>\n</expert>'
                )
                outputs.append(
                    (f"Expert File Summaries: {expert.name}", summaries_by_file)
                )

            # NOTE: should final summary be structured while running summary is natural language? that sounds nice
            #   for RAG, multiple phrasings would make sense but can prob do that later?
            final_summary_prompt = FINAL_SUMMARY_PROMPT.format(
                role=context,
                project_description=project_description,
                codebase_paths="\n".join(parsed_tree.entities_by_file.keys()),
                expert_summaries="\n".join(expert_summaries),
            )
            final_summary_response = await ask_openai(
                final_summary_prompt, SYSTEM_PROMPT
            )
            final_summary = XMLTagContentParser(tag="finalSummary").parse(
                final_summary_response, inclusive=False
            )
        finally:
            output_display = []
            for output in outputs:
                output_display.append(f"### {output[0]}")
                for filename, summary in output[1].items():
                    output_display.append(f"file: {filename}\n{summary}\n-----")
            self.store_output("\n".join(output_display) + "\n" + final_summary)
        return {"summary": final_summary}

import json

from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.common import TypedArgument
from roster_agent_runtime.models.files import FileContents

from ..parsers.code import CodeOutput
from ..parsers.plan import ImplementationPlanParser
from ..parsers.xml import XMLTagContentParser
from ..util.file_tools import find_matches
from ..util.llm import ask_openai
from .base import SYSTEM_PROMPT, BaseLocalAgentAction, LocalAgentAction

logger = app_logger()

CREATE_FILE_PROMPT_TEMPLATE = """
Role: {role}

## Instructions
Your task is to write the file: {filename} according to the implementation plan provided.
You can trust that the changes described in the implementation plan have already been implemented correctly,
aside from the changes that you should make to the current file.
Write code enclosed in an XML 'code' tag as shown in the Format example, keeping in mind the following rules and requirements.
* Implement the current file ONLY.
* The file must be syntactically valid. Do NOT add any content after the last line of code.
* Pay extremely close attention to the provided implementation plan.
* Think step by step before writing. Consider what needs to be implemented, and what your preferred design will be.
* Tip: CAREFULLY check that all references made in the file actually exist, and that you only use existing APIs.

-----
## Implementation Plan
{implementation_plan}
-----
## Format example
-----
## Code: {filename}
<code>
[your code here]
</code>"""

EXTRACT_SNIPPETS_PROMPT = """
Role: {role}

## Instructions
You will be given the current contents of {filename}
Your task is to select portions of this file which should be modified in order to execute the implementation plan below.
You can trust that the other changes described in the implementation plan have already been implemented correctly,
aside from the changes that should be made to the current file.
Paste each portion of the file into an XML 'snippet' tag as shown in the Format example, keeping in mind the following rules and requirements.
* Pay extremely close attention to the provided implementation plan.
* Think step by step before writing. Consider what needs to be implemented, and what your preferred design might be.
* DO NOT select any snippets with the sole intent to refactor or fix any apparent design issues or bugs, UNLESS they directly inhibit your ability to follow the implementation plan.

-----
## Implementation Plan
{implementation_plan}
-----
## Current contents of {filename}
{file_contents}
-----
## Format example
<snippet>
[first snippet]
</snippet>
<snippet>
[second snippet]
</snippet>
"""

MODIFY_SNIPPETS_PROMPT_TEMPLATE = """
Role: {role}

## Instructions
You will be given snippets of {filename}
Your task is to modify each of these snippets (if necessary) in order to execute the implementation plan below.
You can trust that the other changes described in the implementation plan have already been implemented correctly,
aside from the changes that you should make to the current file.
Each snippet will be provided in an XML 'snippet' tag (under 'Extracted Snippets), and you should provide the modified snippets (with your changes) within XML 'updated_snippet' tags as shown in the Format Example.
Keep in mind the following rules and requirements.
* Pay extremely close attention to the provided implementation plan.
* Think step by step before writing. Consider what needs to be implemented, and what your preferred design might be.
* DO NOT refactor or fix any apparent design issues or bugs, UNLESS they directly inhibit your ability to follow the implementation plan.

-----
## Implementation Plan
{implementation_plan}
-----
## Extracted Snippets
{extracted_snippets}
-----
## Format example
<updated_snippet>
[first snippet with your changes, if any]
</updated_snippet>
<updated_snippet>
[second snippet with your changes, if any]
</updated_snippet>
"""


class DummyWriteCode(LocalAgentAction):
    KEY = "WriteCode"

    async def execute(
        self,
        inputs: dict[str, str],
        context: str = "",
    ) -> dict[str, str]:
        with open("code_output.txt", "r") as f:
            code = f.read()
            code_output = {
                "kind": "new_file",
                "filepath": "blackjack.py",
                "content": code,
            }
            return {"code": json.dumps(code_output)}


class WriteCode(BaseLocalAgentAction):
    KEY = "WriteCode"
    SIGNATURE = (
        (TypedArgument.text("implementation_plan"),),
        (TypedArgument.code("code"),),
    )

    async def execute(
        self,
        inputs: dict[str, str],
        context: str = "",
    ) -> dict[str, str]:
        try:
            implementation_plan = inputs["implementation_plan"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")

        code_outputs = []
        implementation_actions = ImplementationPlanParser.parse(implementation_plan)
        modified_filenames = [
            action.filename
            for action in implementation_actions
            if action.type == "modify"
        ]
        # TODO: raise an error if message router isn't running/listening for Agent
        #   might need a timeout instead/in addition
        logger.debug("(write-code) About to read files: %s", modified_filenames)
        file_contents = await self.agent.read_files(
            filepaths=modified_filenames,
            record_id=self.record_id,
            workflow=self.workflow,
        )
        logger.debug("(write-code) Read files: %s", modified_filenames)
        file_contents_by_name: dict[str, FileContents] = {
            file_content.filename: file_content for file_content in file_contents
        }

        for action in implementation_actions:
            if action.type == "create":
                prompt = CREATE_FILE_PROMPT_TEMPLATE.format(
                    role=context,
                    filename=action.filename,
                    implementation_plan=implementation_plan,
                )
                output = await ask_openai(prompt, SYSTEM_PROMPT)
                code_content = XMLTagContentParser(tag="code").parse(
                    output, inclusive=False
                )
                code_outputs.append(
                    CodeOutput(
                        kind="new_file", filepath=action.filename, content=code_content
                    )
                )
            elif action.type == "modify":
                # TODO: handle files which are too long via chunking
                current_file_content = file_contents_by_name[action.filename].text
                current_file_lines = current_file_content.split("\n")
                extract_snippet_prompt = EXTRACT_SNIPPETS_PROMPT.format(
                    role=context,
                    filename=action.filename,
                    implementation_plan=implementation_plan,
                    file_contents=current_file_content,
                )
                extract_snippet_response = await ask_openai(
                    extract_snippet_prompt, SYSTEM_PROMPT
                )
                snippets = list(
                    XMLTagContentParser(tag="snippet").matches(
                        extract_snippet_response, inclusive=False
                    )
                )
                if not snippets:
                    # LLM output did not contain well-formatted spans to modify,
                    # so we make no modifications
                    code_outputs.append(
                        CodeOutput(
                            kind="modify_file",
                            filepath=action.filename,
                            content=current_file_content,
                        )
                    )
                    continue
                snippet_spans = find_matches(snippets, current_file_content)
                if not snippet_spans:
                    raise RuntimeError(
                        f"Could not match snippets in file ({action.filename}) content.\nSnippets: {snippets}"
                    )
                extracted_snippets = "\n".join(
                    (
                        "<snippet>\n{snippet_lines}\n</snippet>".format(
                            snippet_lines="\n".join(
                                current_file_lines[span.start : span.end + 1]
                            )
                        )
                        for span in snippet_spans
                    )
                )
                modify_snippet_prompt = MODIFY_SNIPPETS_PROMPT_TEMPLATE.format(
                    role=context,
                    filename=action.filename,
                    implementation_plan=implementation_plan,
                    extracted_snippets=extracted_snippets,
                )
                modify_snippet_response = await ask_openai(
                    modify_snippet_prompt, SYSTEM_PROMPT
                )
                modified_snippets = list(
                    XMLTagContentParser(tag="updated_snippet").matches(
                        modify_snippet_response, inclusive=False
                    )
                )
                prev_span_end = -1
                modified_file_content = []
                for i, span in enumerate(snippet_spans):
                    modified_file_content.append(
                        "\n".join(current_file_lines[prev_span_end + 1 : span.start])
                    )
                    # NOTE: some concern about mismatching indices here, hopefully not
                    #   a common error case (otherwise might need another fuzzy match round)
                    modified_file_content.append(modified_snippets[i])
                    prev_span_end = span.end
                assert (
                    snippet_spans
                ), f"Missing snippet spans when constructing modified file ({action.filename})"
                modified_file_content.append(
                    "\n".join(current_file_lines[snippet_spans[-1].end + 1 :])
                )
                code_outputs.append(
                    CodeOutput(
                        kind="modify_file",
                        filepath=action.filename,
                        content="".join(modified_file_content),
                    )
                )
            elif action.type == "delete":
                code_outputs.append(
                    CodeOutput(kind="delete_file", filepath=action.filename)
                )
            else:
                raise ValueError(f"Invalid action type: {action.type}")

        final_code_output = json.dumps(
            [code_output.dict() for code_output in code_outputs]
        )
        self.store_output(final_code_output)
        return {"code": final_code_output}

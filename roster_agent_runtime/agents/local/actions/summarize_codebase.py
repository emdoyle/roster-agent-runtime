from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.common import TypedArgument

from ..parsers.codebase_tree import CodebaseTreeParser
from ..parsers.experts import ExpertsParser
from .base import BaseLocalAgentAction

logger = app_logger()


PROMPT_TEMPLATE = """"""


class SummarizeCodebase(BaseLocalAgentAction):
    KEY = "SummarizeCodebase"
    SIGNATURE = (
        (
            TypedArgument.text("codebase_tree"),
            TypedArgument.text("experts"),
        ),
        (TypedArgument.text("summary"),),
    )

    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        try:
            codebase_tree = inputs["codebase_tree"]
            experts = inputs["experts"]
        except KeyError as e:
            raise KeyError(f"Missing required input for {self.KEY}: {e}")

        parsed_tree = CodebaseTreeParser.parse(codebase_tree)
        parsed_experts = ExpertsParser.parse(experts)

        for expert in parsed_experts:
            filtered_tree = parsed_tree.filtered_tree(expert.entities)
            ...

        # TODO:
        # 1. [DONE] iterate over the experts
        # 2. [DONE] select the portion of the codebase tree applicable to the current Expert
        # 3. provide Expert description and codebase tree, describe task is to explore and summarize, ask for first file
        # 4. provide Expert description, codebase tree, file contents (potentially chunked), ask for summary info
        #    and ask for next file to read if applicable [can this be outside of Expert's domain?]
        # 5. repeat (providing the running summary with each subsequent file) until all files in domain have been seen
        # 6. ask for final summary, add it to results and tag it for current Expert
        # 7. after all Experts provide final summaries, aggregate into full codebase summary?
        #    (concern about context length)

        # NOTE: should final summary be structured while running summary is natural language? that sounds nice
        #   for RAG, multiple phrasings would make sense but can prob do that later?
        self.store_output("TODO")
        return {"summary": "TODO"}

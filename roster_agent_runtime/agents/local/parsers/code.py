import json
from typing import Optional

from pydantic import BaseModel

from roster_agent_runtime.agents.local.parsers.xml import XMLTagContentParser
from roster_agent_runtime.logs import app_logger

logger = app_logger()


class CodeOutput(BaseModel):
    kind: str
    filepath: str
    content: str = ""


# No state yet, but just matching pattern of other parsers for now
class CodeOutputParser:
    @classmethod
    def parse(cls, content: str) -> list[CodeOutput]:
        try:
            content_data = json.loads(content)
        except json.JSONDecodeError:
            logger.debug("(code-parse) Could not decode JSON: %s", content)
            raise

        if isinstance(content_data, list):
            return [CodeOutput(**data) for data in content_data]
        return [CodeOutput(**content_data)]


class RefinedCodeResponseParser:
    def __init__(self, tag: str, refinement_declined_phrase: str = "OK"):
        self.refinement_declined_phrase = refinement_declined_phrase
        self.tag = tag
        self._xml_parser = XMLTagContentParser(tag=tag)

    def parse(self, content: str) -> Optional[str]:
        code_contents = self._xml_parser.parse(content, inclusive=False)
        if (
            code_contents.strip().lower()
            == self.refinement_declined_phrase.strip().lower()
        ):
            return None

        return code_contents

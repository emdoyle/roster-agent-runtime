import xml.etree.ElementTree as ElementTree

from pydantic import BaseModel


class ImplementationPlanAction(BaseModel):
    type: str
    filename: str
    plan: str


# No state yet, but just matching pattern of other parsers for now
class ImplementationPlanParser:
    @classmethod
    def parse(cls, content: str) -> list[ImplementationPlanAction]:
        implementation_actions = []
        try:
            root = ElementTree.fromstring(content)
            for action in root:
                implementation_actions.append(
                    ImplementationPlanAction(
                        type=action.tag,
                        filename=action.get("file"),
                        plan=action.text.strip() if action.text else "",
                    )
                )
        except ElementTree.ParseError as e:
            raise ValueError(f"Invalid implementation plan: {e}")
        return implementation_actions

import xml.etree.ElementTree as ElementTree

from pydantic import BaseModel, Field


class ImplementationPlanAction(BaseModel):
    type: str
    filename: str
    plan: str


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


class ExpertInstructions(BaseModel):
    name: str
    text: str
    dependencies: dict[str, str] = Field(default_factory=dict)


def sort_expert_instructions(
    expert_instructions: list[ExpertInstructions],
) -> list[ExpertInstructions]:
    # TODO
    return expert_instructions


class ExpertPlanInstructionsParser:
    @classmethod
    def parse(cls, content: str) -> list[ExpertInstructions]:
        expert_instructions = []
        try:
            root = ElementTree.fromstring(content)
            for expert in root:
                expert_instructions.append(
                    ExpertInstructions(
                        name=expert.get("name"),
                        text=expert.find("instructions").text,
                        dependencies={
                            dep.get("name"): dep.text
                            for dep in expert.findall("dependency")
                        },
                    )
                )
        except ElementTree.ParseError as e:
            raise ValueError(f"Invalid implementation plan: {e}")
        return sort_expert_instructions(expert_instructions)

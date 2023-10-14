import xml.etree.ElementTree as ElementTree

from pydantic import BaseModel, Field


class CodeEntity(BaseModel):
    kind: str
    value: str

    def includes_path(self, path: str) -> bool:
        if self.kind == "directory" and path.startswith(self.value):
            return True
        elif self.kind == "file" and path == self.value:
            return True
        elif self.kind in ["class", "function"] and path == self.value.split(":")[0]:
            return True
        return False


def entity_from_attributes(attributes: dict[str, str]) -> CodeEntity:
    if "dir" in attributes:
        return CodeEntity(kind="directory", value=attributes["dir"])
    elif "file" in attributes:
        return CodeEntity(kind="file", value=attributes["file"])
    elif "class" in attributes:
        return CodeEntity(kind="class", value=attributes["class"])
    elif "function" in attributes:
        return CodeEntity(kind="function", value=attributes["function"])
    return CodeEntity(kind="unknown", value="unknown")


class Expert(BaseModel):
    name: str
    description: str
    entities: list[CodeEntity] = Field(default_factory=list)


class ExpertsParser:
    @classmethod
    def parse(cls, content: str) -> list[Expert]:
        experts = []
        try:
            root = ElementTree.fromstring("<root>" + content + "</root>")
            for expert in root:
                experts.append(
                    Expert(
                        name=expert.get("name"),
                        description=expert.find("description").text,
                        entities=[
                            entity_from_attributes(entity.attrib)
                            for entity in expert.findall("entity")
                        ],
                    )
                )
        except ElementTree.ParseError as e:
            raise ValueError(f"Invalid experts: {e}")
        return experts

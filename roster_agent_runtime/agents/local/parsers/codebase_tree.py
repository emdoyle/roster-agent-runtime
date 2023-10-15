import re

from pydantic import BaseModel, Field

from .experts import CodeEntity


class CodebaseTree(BaseModel):
    entities_by_file: dict[str, str] = Field(default_factory=dict)

    def display(self) -> str:
        result_tree = []
        for filepath, content in self.entities_by_file.items():
            result_tree.append(filepath + "\n" + content)
        return "\n".join(result_tree)

    def filtered_tree(self, entities: list[CodeEntity]) -> "CodebaseTree":
        entities_by_file = {}
        for filepath, contents in self.entities_by_file.items():
            for entity in entities:
                if entity.includes_path(filepath):
                    entities_by_file[filepath] = contents
        return CodebaseTree(entities_by_file=entities_by_file)


ENTITY_REGEX = re.compile(r"^(\w.*):")


class CodebaseTreeParser:
    @classmethod
    def parse(cls, content: str) -> CodebaseTree:
        entities_by_file = {}
        curr_entity = ""
        curr_entity_content = []
        for line in content.splitlines():
            entity_match = ENTITY_REGEX.match(line)
            if entity_match:
                if curr_entity:
                    entities_by_file[curr_entity] = "\n".join(curr_entity_content)
                curr_entity = entity_match.group(1)
                curr_entity_content = []
            else:
                curr_entity_content.append(line)

        if curr_entity:
            entities_by_file[curr_entity] = "\n".join(curr_entity_content)

        return CodebaseTree(entities_by_file=entities_by_file)

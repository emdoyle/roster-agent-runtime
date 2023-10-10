import re
from typing import Generator


class RegexParser:
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.regex = re.compile(pattern, re.DOTALL)

    def parse(self, content: str) -> str:
        content_match = self.regex.search(content)
        return content_match.group(1) if content_match else ""

    def matches(self, content: str) -> Generator[str, None, None]:
        for content_match in self.regex.finditer(content):
            yield content_match.group(1)

import re


class RegexParser:
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.regex = re.compile(pattern, re.DOTALL)

    def parse(self, content: str) -> str:
        output_match = self.regex.search(content)
        return output_match.group(1) if output_match else ""

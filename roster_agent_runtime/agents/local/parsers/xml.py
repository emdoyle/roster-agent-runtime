from .regex import RegexParser


class XMLTagContentParser:
    def __init__(self, tag: str):
        self.tag = tag
        inclusive_pattern = r"(<{tag}>.*?</{tag}>)".format(tag=tag)
        exclusive_pattern = r"<{tag}>(.*?)</{tag}>".format(tag=tag)
        self._inclusive_regex_parser = RegexParser(pattern=inclusive_pattern)
        self._exclusive_regex_parser = RegexParser(pattern=exclusive_pattern)

    def parse(self, content: str, inclusive: bool = True) -> str:
        if inclusive:
            return self._inclusive_regex_parser.parse(content)
        return self._exclusive_regex_parser.parse(content)

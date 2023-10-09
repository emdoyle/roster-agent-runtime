from pydantic import BaseModel
from roster_agent_runtime.logs import app_logger
from thefuzz import fuzz

logger = app_logger()


class Span(BaseModel):
    start: int
    end: int


def best_fit_line(line: str, content: str) -> int:
    content_lines = content.split("\n")
    if not content:
        return -1
    if len(content_lines) <= 1:
        return 0

    best_line = -1
    best_line_ratio = -1
    for i, content_line in enumerate(content_lines):
        line_ratio = fuzz.ratio(line, content_line)
        if line_ratio > best_line_ratio:
            best_line = i
            best_line_ratio = line_ratio

    return best_line


def find_match(snippet: str, content: str) -> Span:
    logger.debug("(find-match) finding match for snippet: %s", snippet)
    snippet_lines = snippet.split("\n")
    if len(snippet_lines) == 1:
        best_fit = best_fit_line(snippet_lines[0], content)
        logger.debug("(find-match) returning single line best fit: %s", best_fit)
        return Span(start=best_fit, end=best_fit)

    best_starting_line = best_fit_line(snippet_lines[0], content)
    best_ending_line = best_fit_line(
        snippet_lines[-1], content[best_starting_line + 1 :]
    )

    logger.debug(
        "(find-match) returning multi line best fit: %s -> %s",
        best_starting_line,
        best_ending_line,
    )
    return Span(start=best_starting_line, end=best_ending_line)


def find_matches(snippets: list[str], content: str) -> list[Span]:
    return list(map(lambda snippet: find_match(snippet, content), snippets))

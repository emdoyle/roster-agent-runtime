from .actions.suggest_experts import SuggestExperts
from .actions.summarize_codebase import SummarizeCodebase
from .base import BaseLocalAgent


class SoftwareArchitect(BaseLocalAgent):
    NAME = "Software Architect"
    ACTIONS = [SuggestExperts, SummarizeCodebase]
    AGENT_CONTEXT = {}


AGENT_CLASS = SoftwareArchitect

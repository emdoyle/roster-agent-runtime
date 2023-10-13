from .actions.identify_domains import IdentifyDomains
from .actions.summarize_codebase import SummarizeCodebase
from .base import BaseLocalAgent


class SoftwareArchitect(BaseLocalAgent):
    NAME = "Software Architect"
    ACTIONS = [IdentifyDomains, SummarizeCodebase]
    AGENT_CONTEXT = {}


AGENT_CLASS = SoftwareArchitect

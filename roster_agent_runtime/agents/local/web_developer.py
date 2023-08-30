from .actions.refine_code import RefineCode
from .actions.write_code import WriteCode
from .base import BaseLocalAgent


class WebDeveloper(BaseLocalAgent):
    NAME = "Web Developer"
    ACTIONS = [WriteCode, RefineCode]
    AGENT_CONTEXT = {}


AGENT_CLASS = WebDeveloper

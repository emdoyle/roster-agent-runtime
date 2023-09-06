from .actions.plan_code_changes import PlanCodeChanges
from .actions.refine_code import RefineCode
from .actions.write_code import WriteCode
from .base import BaseLocalAgent


class WebDeveloper(BaseLocalAgent):
    NAME = "Web Developer"
    ACTIONS = [PlanCodeChanges, WriteCode, RefineCode]
    AGENT_CONTEXT = {}


AGENT_CLASS = WebDeveloper

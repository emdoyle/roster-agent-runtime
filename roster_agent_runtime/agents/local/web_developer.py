from .actions.plan_code_changes import DummyPlanCodeChanges, PlanCodeChanges
from .actions.refine_code import DummyRefineCode, RefineCode
from .actions.write_code import WriteCode
from .base import BaseLocalAgent


class WebDeveloper(BaseLocalAgent):
    NAME = "Web Developer"
    ACTIONS = [DummyPlanCodeChanges, WriteCode, DummyRefineCode]
    AGENT_CONTEXT = {}


AGENT_CLASS = WebDeveloper

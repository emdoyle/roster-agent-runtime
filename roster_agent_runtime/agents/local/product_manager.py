from .actions.write_prd import WritePRD
from .base import BaseLocalAgent


class ProductManager(BaseLocalAgent):
    NAME = "Product Manager"
    ACTIONS = [WritePRD]
    AGENT_CONTEXT = {}


AGENT_CLASS = ProductManager

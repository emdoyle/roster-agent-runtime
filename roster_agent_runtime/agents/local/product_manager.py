from .actions.write_prd import DummyWritePRD, WritePRD
from .base import BaseLocalAgent


class ProductManager(BaseLocalAgent):
    NAME = "Product Manager"
    ACTIONS = [DummyWritePRD]
    AGENT_CONTEXT = {}


AGENT_CLASS = ProductManager

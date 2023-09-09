from abc import ABC, abstractmethod

from roster_agent_runtime.agents.local.base import LocalAgent
from roster_agent_runtime.logs import app_logger

logger = app_logger()

# TODO: where should this live?
SYSTEM_PROMPT = """This conversation is happening within a system called Roster,
and you are acting as an Agent in this system. The User is a human being who is
operating the system and is trying to accomplish a software development task. The User will provide
guidance on your role in the system, and describe the task at hand. You will
perform the task to the best of your ability, paying close attention to all instructions."""


class LocalAgentAction(ABC):
    KEY = NotImplemented

    @abstractmethod
    async def execute(
        self,
        inputs: dict[str, str],
        context: str = "",
    ) -> dict[str, str]:
        ...


class BaseLocalAgentAction(LocalAgentAction, ABC):
    def __init__(
        self, agent: LocalAgent, record_id: str, workflow: str, *args, **kwargs
    ):
        self.agent = agent
        self.record_id = record_id
        self.workflow = workflow

    # quick-and-dirty for local observability
    def store_output(self, output: str):
        with open(f"action_outputs/{self.KEY}/{self.record_id}.txt") as f:
            f.write(output)

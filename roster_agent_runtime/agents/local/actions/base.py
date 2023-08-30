from abc import ABC, abstractmethod

# TODO: where should this live?
SYSTEM_PROMPT = """This conversation is happening within a system called Roster,
and you are acting as an Agent in this system. The User is a human being who is
operating the system and is trying to accomplish a task. The User will provide
guidance on your role in the system, and describe the task at hand. You will
perform the task to the best of your ability, paying close attention to all instructions."""


class LocalAgentAction(ABC):
    KEY = NotImplemented

    @abstractmethod
    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        ...

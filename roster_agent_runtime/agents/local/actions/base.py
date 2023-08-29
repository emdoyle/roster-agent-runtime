from abc import ABC, abstractmethod


class LocalAgentAction(ABC):
    KEY = NotImplemented

    @abstractmethod
    async def execute(
        self, inputs: dict[str, str], context: str = ""
    ) -> dict[str, str]:
        ...

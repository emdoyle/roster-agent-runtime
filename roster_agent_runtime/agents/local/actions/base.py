from abc import ABC, abstractmethod
from typing import Optional


class LocalAgentAction(ABC):
    KEY = NotImplemented

    @abstractmethod
    async def execute(
        self, inputs: dict[str, str], context: Optional[dict] = None
    ) -> dict[str, str]:
        ...

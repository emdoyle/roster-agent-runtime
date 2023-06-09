from abc import ABC, abstractmethod
from typing import Callable, Generic, TypeVar

E = TypeVar("E")
T = TypeVar("T")


class Informer(ABC, Generic[T, E]):
    @abstractmethod
    async def setup(self):
        """setup informer -- called once on startup to establish listeners on remote data source"""

    @abstractmethod
    async def add_event_listener(self, callback: Callable[[E], None]):
        """add callback to be called when informer receives an object"""

    @abstractmethod
    def list(self) -> list[T]:
        """list all objects"""

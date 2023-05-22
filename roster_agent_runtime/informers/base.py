from abc import ABC, abstractmethod
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


# NOTE: probably need to reconcile the concept of an 'Event' with 'Object'
#   Events are things that happen, Objects are things that exist


class Informer(ABC, Generic[T]):
    @abstractmethod
    async def setup(self):
        """setup informer -- called once on startup to establish listeners on remote data source"""

    @abstractmethod
    async def add_event_listener(self, callback: Callable[[T], None]):
        """add callback to be called when informer receives an object"""

    @abstractmethod
    def list(self) -> list[T]:
        """list all objects"""

    @abstractmethod
    def get(self, id: str) -> T:
        """get object"""

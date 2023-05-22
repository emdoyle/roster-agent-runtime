import asyncio
from typing import Callable, Optional

import aiohttp

from .stream import JSONStream

DEFAULT_EVENT_FILTERS = {
    "type": "container",
    "event": ["start", "stop", "die", "destroy"],
}


class DockerEventListener:
    def __init__(
        self,
        filters: Optional[dict] = None,
        middleware: Optional[list[Callable]] = None,
        handlers: Optional[list[Callable]] = None,
    ):
        self.filters = filters or DEFAULT_EVENT_FILTERS
        self.middleware = middleware or []
        self.handlers = handlers or []
        # NOTE: This means an instance should only be used once
        self.task = None
        self.json_stream = None

    async def listen(self):
        if self.json_stream is not None:
            raise RuntimeError("DockerEventListener already listening for events")
        async with aiohttp.ClientSession(
            connector=aiohttp.UnixConnector(path="/var/run/docker.sock")
        ) as session:
            async with session.get(
                "http://localhost/events",
                headers={"Content-Type": "application/json"},
                params={**self.filters, "stream": "1"},
                timeout=0,
            ) as resp:
                self.json_stream = JSONStream(resp)
                try:
                    async for event in self.json_stream:
                        for middleware in self.middleware:
                            event = await middleware(event)
                        for handler in self.handlers:
                            await handler(event)
                finally:
                    self.json_stream = None

    def run_as_task(self) -> asyncio.Task:
        if self.task is not None:
            raise RuntimeError("Informer task already exists")
        loop = asyncio.get_event_loop()
        self.task = loop.create_task(self.listen())
        return self.task

    def stop(self):
        if self.task is not None:
            self.task.cancel()
            self.task = None

    def add_middleware(self, middleware: Callable):
        self.middleware.append(middleware)

    def add_handler(self, handler: Callable):
        self.handlers.append(handler)

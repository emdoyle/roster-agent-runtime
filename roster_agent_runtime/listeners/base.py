import asyncio
from typing import Callable, Optional

import aiohttp


class EventListener:
    def __init__(
        self,
        url: str,
        middleware: Optional[list[Callable]] = None,
        handlers: Optional[list[Callable]] = None,
    ):
        self.url = url
        self.middleware = middleware or []
        self.handlers = handlers or []
        # NOTE: This means an instance should only be used once
        self.task = None

    async def listen(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as resp:
                async for line in resp.content:
                    if line == b"\n":
                        continue
                    for handler in self.handlers:
                        line = line.decode("utf-8")
                        for middleware in self.middleware:
                            line = await middleware(line)
                        await handler(line)

    def run_as_task(self) -> asyncio.Task:
        if self.task is not None:
            raise RuntimeError("Informer task already exists")
        loop = asyncio.get_event_loop()
        self.task = loop.create_task(self.listen())
        return self.task

    def stop(self):
        if self.task is None:
            raise RuntimeError("Informer task does not exist")
        self.task.stop()

    def add_middleware(self, middleware: Callable):
        self.middleware.append(middleware)

    def add_handler(self, handler: Callable):
        self.handlers.append(handler)

import asyncio
import urllib.parse
from typing import Callable, Optional

import aiohttp
from roster_agent_runtime.logs import app_logger

logger = app_logger()


class EventListener:
    def __init__(
        self,
        url: str,
        params: Optional[dict] = None,
        middleware: Optional[list[Callable]] = None,
        handlers: Optional[list[Callable]] = None,
    ):
        if params:
            url = url + "?" + urllib.parse.urlencode(params, doseq=True)
        self.url = url
        self.middleware = middleware or []
        self.handlers = handlers or []
        # NOTE: This means an instance should only be used once
        self.task = None

    async def listen(self):
        async with aiohttp.ClientSession() as session:
            logger.debug("(evt-listen) Listening to events from %s", self.url)
            async with session.get(self.url) as resp:
                async for line in resp.content:
                    if line == b"\n":
                        continue
                    line = line.decode("utf-8").strip()
                    logger.debug("(evt-listen) [%s] Line: %s", self.url, line)
                    for handler in self.handlers:
                        try:
                            for middleware in self.middleware:
                                line = middleware(line)
                            handler(line)
                        except Exception:
                            logger.error(
                                "(evt-listen) [%s] Error handling event: %s",
                                self.url,
                                line,
                            )

    def run_as_task(self) -> asyncio.Task:
        if self.task is not None:
            raise RuntimeError("Informer task already exists")
        loop = asyncio.get_event_loop()
        self.task = loop.create_task(self.listen())
        return self.task

    def stop(self):
        if self.task is None:
            raise RuntimeError("Informer task does not exist")
        self.task.cancel()

    def add_middleware(self, middleware: Callable):
        self.middleware.append(middleware)

    def add_handler(self, handler: Callable):
        self.handlers.append(handler)

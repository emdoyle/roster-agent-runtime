import asyncio

import aiohttp

from roster_agent_runtime import settings
from roster_agent_runtime.controllers.events.status import ControllerStatusEvent
from roster_agent_runtime.logs import app_logger

logger = app_logger()


class RosterNotifier:
    def __init__(self, url: str = settings.ROSTER_API_STATUS_UPDATE_URL):
        self.url = url
        self.task = None
        self._event_queue = None

    def push_event(self, event: ControllerStatusEvent):
        if self._event_queue is None:
            raise RuntimeError("RosterStatusChangeNotifier not started")
        event_data = event.dict()
        self._event_queue.put_nowait(event_data)

    async def start(self):
        self._event_queue = asyncio.Queue()
        while True:
            payload = await self._event_queue.get()
            logger.debug("(rstr-notif) Sending status event %s", payload)
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(self.url, json=payload, raise_for_status=True)
            except Exception as e:
                logger.warn(
                    "(rstr-notif) Failed to send status event to %s\n%s", self.url, e
                )
                pass

    def setup(self):
        if self.task is not None:
            raise RuntimeError("RosterStatusChangeNotifier already started")
        self.task = asyncio.create_task(self.start())

    def teardown(self):
        if self.task is not None:
            self.task.cancel()
            self.task = None

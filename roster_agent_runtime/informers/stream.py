import json

import aiohttp


class JSONStream:
    def __init__(self, response: aiohttp.ClientResponse):
        self.response = response

    def __aiter__(self):
        return self

    async def __anext__(self):
        line = await self.response.content.readline()
        if not line:
            raise StopAsyncIteration
        return json.loads(line.decode("utf-8"))

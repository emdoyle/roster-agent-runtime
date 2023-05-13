import asyncio


async def aretry(func, max_retries=5, delay=1):
    retries = 0
    while retries < max_retries:
        try:
            return await func()
        except Exception as e:
            retries += 1
            if retries >= max_retries:
                raise e
            await asyncio.sleep(delay)

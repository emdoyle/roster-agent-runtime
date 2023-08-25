def make_async(func):
    async def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper

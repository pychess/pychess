import asyncio


def create_task(coro):
    return asyncio.get_event_loop().create_task(coro)

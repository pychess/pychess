import asyncio
import sys

if sys.version_info < (3, 7, 0):
    def create_task(coro):
        return asyncio.get_event_loop().create_task(coro)
else:
    create_task = asyncio.create_task

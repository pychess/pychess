import asyncio
import unittest

from pychess.System import cancel_all_tasks


class AsyncShutdownTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_all_tasks_cancels_pending_tasks_before_draining(self):
        started = []

        async def worker(index):
            started.append(index)
            await asyncio.Future()

        tasks = [asyncio.create_task(worker(index)) for index in range(20)]

        await cancel_all_tasks()

        self.assertEqual(started, [])
        self.assertTrue(all(task.cancelled() for task in tasks))

    async def test_cancel_all_tasks_waits_for_spawned_cleanup(self):
        cleanup_done = asyncio.Event()

        async def worker():
            try:
                await asyncio.Future()
            except asyncio.CancelledError:

                async def cleanup():
                    await asyncio.sleep(0)
                    cleanup_done.set()

                asyncio.create_task(cleanup())
                raise

        asyncio.create_task(worker())
        await asyncio.sleep(0)

        await cancel_all_tasks()

        self.assertTrue(cleanup_done.is_set())


if __name__ == "__main__":
    unittest.main()

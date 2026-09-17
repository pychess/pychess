import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import gi

gi.require_version("Gtk", "3.0")

from pychess.perspectives.learn import SolvingProgress
from pychess.perspectives.learn.generateLessonsSidepanel import generateLessonsSidepanel
from pychess.Utils.const import LESSON, PUZZLE


class LearnProgressTests(unittest.IsolatedAsyncioTestCase):
    async def check_panel(self, category, progress_file, saved, preload=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / progress_file
            if saved is not None:
                path.write_text(json.dumps(saved))

            progress = SolvingProgress(str(path))
            if preload:
                progress.read_all()
            entries = [("first.pgn", "First", "Test"), ("second.pgn", "Second", "Test")]
            panel = generateLessonsSidepanel(progress, category, entries, None)()

            # Capture and await the actual loading task so its exceptions fail
            # the test instead of becoming "exception was never retrieved" logs.
            create_task = asyncio.create_task
            tasks = []

            def schedule(coro):
                task = create_task(coro)
                tasks.append(task)
                return task

            with (
                patch.object(progress, "get_count", return_value=3),
                patch(
                    "pychess.perspectives.learn.generateLessonsSidepanel.asyncio.create_task",
                    side_effect=schedule,
                ),
            ):
                widget = panel.load(None)
                try:
                    self.assertEqual(len(tasks), 1)
                    await asyncio.wait_for(tasks[0], timeout=5)
                    expected = {
                        filename: (saved or {}).get(filename, [0, 0, 0])
                        for filename, _, _ in entries
                    }
                    self.assertEqual([row[0] for row in panel.store], list(expected))
                    for row in panel.store:
                        solved = expected[row[0]].count(1)
                        self.assertEqual(row[3], f"{solved} / 3")
                        self.assertEqual(row[4], round(solved * 100 / 3))
                    self.assertEqual(json.loads(path.read_text()), expected)
                finally:
                    widget.destroy()

    async def test_fresh_profile(self):
        for category, filename in ((PUZZLE, "puzzles.json"), (LESSON, "lessons.json")):
            with self.subTest(filename=filename):
                await self.check_panel(category, filename, None)

    async def test_saved_progress_on_reopen(self):
        await self.check_panel(PUZZLE, "puzzles.json", {"first.pgn": [1, 0, 1]})

    async def test_partially_initialized_collection(self):
        await self.check_panel(
            LESSON, "lessons.json", {"first.pgn": [1, 0, 1]}, preload=True
        )


if __name__ == "__main__":
    unittest.main()

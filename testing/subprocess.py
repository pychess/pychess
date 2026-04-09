import asyncio
import sys
import unittest

from pychess.System.SubProcess import SubProcess


HELPER_CODE = """\
import sys

print("ready", flush=True)
for line in sys.stdin:
    if line.strip() == "quit":
        print("bye", flush=True)
        raise SystemExit(0)
"""


class SubProcessTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.subprocesses = []

    async def asyncTearDown(self):
        for subproc in self.subprocesses:
            if subproc.proc.returncode is None:
                subproc.proc.kill()
                await subproc.proc.wait()

    async def start_subprocess(self):
        subproc = SubProcess(
            sys.executable,
            args=["-c", HELPER_CODE],
            cwd=".",
        )
        self.subprocesses.append(subproc)
        await subproc.start()
        return subproc

    async def terminate_and_wait(self, subproc):
        subproc.terminate()
        await asyncio.wait_for(subproc.terminate_task, 2.0)
        await asyncio.wait_for(subproc.proc.wait(), 2.0)

    async def test_terminate_waits_for_graceful_quit(self):
        subproc = await self.start_subprocess()
        subproc.write("quit\n")

        await self.terminate_and_wait(subproc)

        self.assertEqual(subproc.proc.returncode, 0)

    @unittest.skipIf(sys.platform == "win32", "Uses SIGSTOP/SIGCONT semantics")
    async def test_terminate_resumes_paused_process(self):
        subproc = await self.start_subprocess()
        subproc.pause()
        await asyncio.sleep(0.05)
        subproc.write("quit\n")

        await self.terminate_and_wait(subproc)

        self.assertEqual(subproc.proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()

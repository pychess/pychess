import asyncio
import os
import psutil
import signal
import subprocess
import sys
import time

from gi.repository import GObject, GLib

from pychess.System.Log import log
from pychess.Players.ProtocolEngine import TIME_OUT_SECOND


class SubProcess(GObject.GObject):
    QUIT_TIMEOUT = 0.5
    TERM_TIMEOUT = 1.0
    KILL_TIMEOUT = 1.0

    __gsignals__ = {
        "line": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "died": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(
        self, path, args=[], warnwords=[], env=None, cwd=".", lowPriority=False
    ):
        GObject.GObject.__init__(self)

        self.path = path
        self.args = args
        self.warnwords = warnwords
        self.env = env or os.environ
        self.cwd = cwd
        self.lowPriority = lowPriority

        self.defname = os.path.split(path)[1]
        self.defname = self.defname[:1].upper() + self.defname[1:].lower()
        cur_time = time.time()
        self.defname = (
            self.defname,
            time.strftime("%H:%m:%%.3f", time.localtime(cur_time)) % (cur_time % 60),
        )
        log.debug(path + " " + " ".join(self.args), extra={"task": self.defname})

        self.argv = [str(u) for u in [self.path] + self.args]
        self.terminated = False
        self.read_stdout_task = None
        self.write_task = None
        self.terminate_task = None

    def __del__(self):
        if hasattr(self, "proc"):
            self._close_transport()

    async def start(self):
        log.debug(
            "SubProcess.start(): create_subprocess_exec...",
            extra={"task": self.defname},
        )
        if sys.platform == "win32":
            # To prevent engines opening console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            startupinfo = None

        create = asyncio.create_subprocess_exec(
            *self.argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            startupinfo=startupinfo,
            env=self.env,
            cwd=self.cwd,
        )
        try:
            self.proc = await asyncio.wait_for(create, TIME_OUT_SECOND)
            self.pid = self.proc.pid
            # print(self.pid, self.path)
            if self.lowPriority:
                proc = psutil.Process(self.pid)
                if sys.platform == "win32":
                    niceness = psutil.BELOW_NORMAL_PRIORITY_CLASS
                else:
                    niceness = 15  # The higher, the lower the priority
                if psutil.__version__ >= "2.0.0":
                    proc.nice(niceness)
                else:
                    proc.set_nice(niceness)
            self.read_stdout_task = asyncio.create_task(
                self.read_stdout(self.proc.stdout)
            )
        except asyncio.TimeoutError:
            log.warning("TimeoutError", extra={"task": self.defname})
            raise
        except GLib.GError:
            log.warning("GLib.GError", extra={"task": self.defname})
            raise
        except Exception:
            e = sys.exc_info()[0]
            log.warning("%s" % e, extra={"task": self.defname})
            raise

    def write(self, line):
        if self.terminated:
            return
        self.write_task = asyncio.create_task(self.write_stdin(self.proc.stdin, line))

    async def write_stdin(self, writer, line):
        try:
            log.debug(line, extra={"task": self.defname})
            writer.write(line.encode())
            await writer.drain()
        except BrokenPipeError:
            log.debug(
                "SubProcess.write_stdin(): BrokenPipeError",
                extra={"task": self.defname},
            )
            self.emit("died")
            self.terminate()
        except ConnectionResetError:
            log.debug(
                "SubProcess.write_stdin(): ConnectionResetError",
                extra={"task": self.defname},
            )
            self.emit("died")
            self.terminate()
        except GLib.GError:
            log.debug(
                "SubProcess.write_stdin(): GLib.GError", extra={"task": self.defname}
            )
            self.emit("died")
            self.terminate()

    async def read_stdout(self, reader):
        try:
            while True:
                line = await reader.readline()
                if line:
                    await asyncio.sleep(0)

                    try:
                        line = line.decode().rstrip()
                        # print(line)
                    except UnicodeError:
                        # Some engines send author names in different encodinds (f.e. spike)
                        print("UnicodeError while decoding:", line)
                        continue

                    if not line:
                        continue

                    for word in self.warnwords:
                        if word in line:
                            log.debug(line, extra={"task": self.defname})
                            break
                    else:
                        log.debug(line, extra={"task": self.defname})
                    self.emit("line", line)
                else:
                    self.emit("died")
                    break
        except asyncio.CancelledError:
            self._close_transport()
            raise
        self.terminate()

    def terminate(self):
        if self.terminated:
            return

        try:
            if self.proc.returncode is not None:
                self.terminated = True
                self._close_transport()
                return
        except ProcessLookupError:
            self.terminated = True
            self._close_transport()
            return

        self.terminated = True
        self.resume()
        self.terminate_task = asyncio.create_task(self._terminate())

    def _close_transport(self):
        transport = getattr(self.proc, "_transport", None)
        if transport is not None:
            popen = getattr(transport, "_proc", None)
            if popen is not None:
                for pipe in (popen.stdin, popen.stdout, popen.stderr):
                    if pipe is not None:
                        pipe.close()
            transport.close()

    async def _wait_for_exit(self, timeout):
        try:
            await asyncio.wait_for(self.proc.wait(), timeout)
        except asyncio.TimeoutError:
            return False
        else:
            return True

    async def _terminate(self):
        current = asyncio.current_task()

        try:
            if self.write_task is not None and self.write_task is not current:
                log.debug(
                    "SubProcess.terminate(): waiting for pending write",
                    extra={"task": self.defname},
                )
                try:
                    await asyncio.wait_for(
                        asyncio.shield(self.write_task), self.QUIT_TIMEOUT
                    )
                except (
                    asyncio.TimeoutError,
                    asyncio.CancelledError,
                    BrokenPipeError,
                    ConnectionResetError,
                    GLib.GError,
                ):
                    pass

            if self.proc.stdin is not None:
                try:
                    self.proc.stdin.close()
                    await self.proc.stdin.wait_closed()
                except (BrokenPipeError, ConnectionResetError):
                    pass

            if await self._wait_for_exit(self.QUIT_TIMEOUT):
                return

            try:
                self.proc.terminate()
                log.debug("SubProcess.terminate()", extra={"task": self.defname})
            except ProcessLookupError:
                log.debug(
                    "SubProcess.terminate(): ProcessLookupError",
                    extra={"task": self.defname},
                )
                return

            if await self._wait_for_exit(self.TERM_TIMEOUT):
                return

            try:
                proc = psutil.Process(self.pid)
                children = proc.children(recursive=True)
            except psutil.Error:
                children = []

            try:
                self.proc.kill()
                log.debug("SubProcess.kill()", extra={"task": self.defname})
            except ProcessLookupError:
                return

            for child in children:
                try:
                    child.kill()
                except psutil.Error:
                    continue

            await self._wait_for_exit(self.KILL_TIMEOUT)
        finally:
            self._close_transport()

    def pause(self):
        if sys.platform != "win32":
            try:
                self.proc.send_signal(signal.SIGSTOP)
            except ProcessLookupError:
                log.debug(
                    "SubProcess.pause(): ProcessLookupError",
                    extra={"task": self.defname},
                )

    def resume(self):
        if sys.platform != "win32":
            try:
                self.proc.send_signal(signal.SIGCONT)
            except ProcessLookupError:
                log.debug(
                    "SubProcess.pause(): ProcessLookupError",
                    extra={"task": self.defname},
                )

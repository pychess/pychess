# -*- coding: UTF-8 -*-

import re
import sys
import shutil

from gi.repository import GObject

from pychess.compat import create_task
from pychess.System.Log import log
from pychess.System.SubProcess import SubProcess


class Pinger(GObject.GObject):
    """ The received signal contains the time it took to get response from the
        server in millisecconds. -1 means that some error occurred """

    __gsignals__ = {
        "received": (GObject.SignalFlags.RUN_FIRST, None, (float, )),
        "error": (GObject.SignalFlags.RUN_FIRST, None, (str, ))
    }

    def __init__(self, host):
        GObject.GObject.__init__(self)
        self.host = host
        self.subproc = None

        self.expression = re.compile("=([\d\.]+) (m?s)")

        # We need untranslated error messages in regexp search
        # below, so have to use deferred translation here
        def _(msg):
            return msg

        error = _("Destination Host Unreachable")
        self.errorExprs = (re.compile("(%s)" % error), )
        del _

        self.restartsOnDead = 3
        self.deadCount = 0

    def start(self):
        assert not self.subproc
        if sys.platform == "win32":
            args = ["-t", self.host]
        else:
            args = ["-i10", self.host]
        self.subproc = SubProcess(shutil.which("ping"), args, env={"LANG": "en"})
        create_task(self.subproc.start())
        self.conid1 = self.subproc.connect("line", self.__handleLines)
        self.conid2 = self.subproc.connect("died", self.__handleDead)

    def __handleLines(self, subprocess, line):
        match = self.expression.search(line)
        if match:
            time, unit = match.groups()
            time = float(time)
            if unit == "s":
                time *= 1000
            self.emit("received", time)
        else:
            for expr in self.errorExprs:
                match = expr.search(line)
                if match:
                    msg = match.groups()[0]
                    self.emit("error", _(msg))

    def __handleDead(self, subprocess):
        if self.deadCount < self.restartsOnDead:
            log.warning("Pinger died and restarted (%d/%d)" %
                        (self.deadCount + 1, self.restartsOnDead),
                        extra={"task": self.subproc.defname})
            self.stop()
            self.start()
            self.deadCount += 1
        else:
            self.emit("error", _("Died"))
            self.stop()

    def stop(self):
        if not self.subproc:
            return
        # exitCode = self.subproc.gentleKill()
        self.subproc.disconnect(self.conid1)
        self.subproc.disconnect(self.conid2)
        self.subproc.terminate()
        self.subproc = None


if __name__ == "__main__":
    pinger = Pinger("google.com")

    def callback(pinger, time):
        print(time)

    pinger.connect("received", callback)
    pinger.start()
    import time
    time.sleep(5)
    pinger.stop()
    time.sleep(3)

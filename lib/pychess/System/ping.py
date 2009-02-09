# -*- coding: UTF-8 -*-

from threading import Thread
from subprocess import *
import select, signal, re, os, atexit

from gobject import GObject, SIGNAL_RUN_FIRST

from pychess.System import glock
from pychess.System.Log import log
from pychess.System.SubProcess import SubProcess, SubProcessError, searchPath
from pychess.System.ThreadPool import PooledThread
from pychess.Utils.const import SUBPROCESS_PTY

class Pinger (GObject):
    """ The recieved signal contains the time it took to get response from the
        server in millisecconds. -1 means that some error occurred """
    
    __gsignals__ = {
        "recieved": (SIGNAL_RUN_FIRST, None, (float,)),
        "error": (SIGNAL_RUN_FIRST, None, (str,))
    }
    
    def __init__ (self, host):
        GObject.__init__(self)
        self.host = host
        self.subproc = None
        
        self.expression = re.compile("time=([\d\.]+) (m?s)")
        self.errorExprs = (
            re.compile("(Destination Host Unreachable)"),
        )
        
        self.restartsOnDead = 3
        self.deadCount = 0
    
    def start (self):
        assert not self.subproc
        self.subproc = SubProcess(searchPath("ping"), [self.host], env={"LANG":"en"})
        self.conid1 = self.subproc.connect("line", self.__handleLines)
        self.conid2 = self.subproc.connect("died", self.__handleDead)

    def __handleLines (self, subprocess, lines):
        for line in lines:
            self.__handleLine(line)
    
    def __handleLine (self, line):
        match = self.expression.search(line)
        if match:
            time, unit = match.groups()
            time = float(time)
            if unit == "s":
                time *= 1000
            self.emit("recieved", time)
        else:
            for expr in self.errorExprs:
                match = expr.search(line)
                if match:
                    self.emit("error", match.groups()[0])
    
    def __handleDead (self, subprocess):
        if self.deadCount < self.restartsOnDead:
            log.warn("Pinger died and restarted (%d/%d)\n" %
                     (self.deadCount+1, self.restartsOnDead),
                     self.subproc.defname)
            self.stop()
            self.start()
            self.deadCount += 1
        else:
            self.emit("error", _("Died"))
            self.stop()
    
    def stop (self):
        assert self.subproc
        exitCode = self.subproc.gentleKill()
        self.subproc.disconnect(self.conid1)
        self.subproc.disconnect(self.conid2)
        self.subproc = None

if __name__ == "__main__":
    pinger = Pinger("google.com")
    def callback(pinger, time):
        print time
    pinger.connect("recieved", callback)
    pinger.start()
    import time
    time.sleep(5)
    pinger.stop()
    time.sleep(3)

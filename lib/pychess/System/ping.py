# -*- coding: UTF-8 -*-

from threading import Thread
from subprocess import *
import select, signal, re, os, atexit

from gobject import GObject, SIGNAL_RUN_FIRST

from pychess.System import glock
from pychess.System.SubProcess import SubProcess, SubProcessError, searchPath
from pychess.System.ThreadPool import PooledThread
from pychess.Utils.const import SUBPROCESS_PTY

class Pinger (GObject, PooledThread):
    """ The recieved signal contains the time it took to get response from the
        server in millisecconds. -1 means that some error occurred """
    
    __gsignals__ = {
        "recieved": (SIGNAL_RUN_FIRST, None, (float,)),
        "error": (SIGNAL_RUN_FIRST, None, (str,))
    }
    
    def __init__ (self, host):
        GObject.__init__(self)
        self.host = host
        self.expression = re.compile("time=([\d\.]+) (m?s)")
        self.subproc = None
        atexit.register(self.stop)
    
    def start (self):
        self.subproc = SubProcess(
                searchPath("ping"), [self.host], env={"LANG":"en"}, type=SUBPROCESS_PTY)
        PooledThread.start(self)
    
    def run (self):
        while True:
            try:
                line = self.subproc.readline()
            except SubProcessError, e:
                glock.acquire()
                try:
                    self.emit("error", ", ".join(e[1]))
                finally:
                    glock.release()
                return
            match = self.expression.search(line)
            if match:
                time, unit = match.groups()
                time = float(time)
                if unit == "s":
                    time *= 1000
                glock.acquire()
                try:
                    self.emit("recieved", time)
                finally:
                    glock.release()
    
    def stop (self):
        if not self.subproc: return
        self.subproc.gentleKill()

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

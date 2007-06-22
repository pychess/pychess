# -*- coding: UTF-8 -*-

from threading import Thread
from subprocess import *
import select, signal, re, os, atexit

from gobject import GObject, SIGNAL_RUN_FIRST

from pychess.System import glock
from pychess.System.SubProcess import SubProcess, SubProcessError, searchPath

class Pinger (GObject):
    """ The recieved signal contains the time it took to get response from the
        server in millisecconds. -1 means that some error occurred """
    
    __gsignals__ = {
        "recieved": (SIGNAL_RUN_FIRST, None, (float,))
    }
    
    def __init__ (self, host):
        GObject.__init__(self)
        self.host = host
        self.expression = re.compile("time=([\d\.]+) (m?s)")
        self.subproc = None
        atexit.register(self.stop)
    
    def start (self):
        thread = Thread(target=self.ping)
        thread.setDaemon(True)
        thread.start()
    
    def ping (self):
        if self.subproc: return
        self.subproc = SubProcess(searchPath("ping"), [self.host], {"LANG":"en"})
        while True:
            line = self.subproc.readline()
            if not globals:
                # If python has been shut down while we were sleeping
                # We better stop pinging
                return
            match = self.expression.search(line)
            if match:
                time, unit = match.groups()
                time = float(time)
                if unit == "s":
                    time *= 1000
                glock.acquire()
                self.emit("recieved", time)
                glock.release()
    
    def stop (self):
        if not self.subproc: return
        self.subproc.sigkill()

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

# -*- coding: UTF-8 -*-

from threading import Thread
from subprocess import *
import select, signal, re, os, atexit

from gobject import GObject, SIGNAL_RUN_FIRST
from gtk.gdk import threads_enter, threads_leave

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
        self.pid = None
        
        atexit.register(self.stop)
        
    def start (self):
        thread = Thread(target=self.ping)
        thread.setDaemon(True)
        thread.start()
    
    def ping (self):
        if self.pid != None:
            return
        popen = Popen(["ping", self.host], env={"LANG":"en"},
                      stdout=PIPE, stderr=PIPE)
        self.pid = popen.pid
        while True:
            try:
                rlist, _,_ = select.select([popen.stdout, popen.stderr], [],[])
            except select.error, error:
                if error.args[0] != 4:
                    # We break on errors besides 4 - Interrupt
                    break
            for pipe in rlist:
                while True:
                    line = pipe.readline()
                    if not line: break
                    if not globals:
                        # If python has been shut down while we were sleeping
                        # We better stop pinging
                        return
                    if pipe == popen.stdout:
                        match = self.expression.search(line)
                        if match:
                            time, unit = match.groups()
                            time = float(time)
                            if unit == "s":
                                time *= 1000
                            threads_enter()
                            self.emit("recieved", time)
                            threads_leave()
                    elif pipe == popen.stderr:
                        threads_enter()
                        self.emit("recieved", -1)
                        threads_leave()
    
    def stop (self):
        os.kill(self.pid, signal.SIGKILL)
        self.pid = None

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

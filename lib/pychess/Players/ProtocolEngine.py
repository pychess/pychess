from gobject import GObject, SIGNAL_RUN_FIRST
from threading import Condition, Lock, RLock

from pychess.System.Log import log
from pychess.Players.Engine import Engine
from pychess.Utils.const import *

class ProtocolEngine (Engine):
    
    NORMAL, ANALYZING, INVERSE_ANALYZING = range(3)
    
    __gsignals__ = {
        'ready':      (SIGNAL_RUN_FIRST, None, ())
    }
    
    def __init__ (self, subprocess, color, protover):
        Engine.__init__(self)
        
        self.engine = subprocess
        self.defname = subprocess.defname[0]
        self.color = color
        self.protover = protover
        
        self.readycon = Condition()
        self.runWhenReadyLock = RLock()
        self.readylist = []
        
        self.ready = False
        self.connected = True
        self.mode = NORMAL
        
        log.debug(reprColor[color]+"\n", self.defname)
        
        self.movecon = Condition()
        self.analyzeMoves = []
        self.name = None
        
        self.connect("ready", self.onReady)
    
    def setName (self, name):
        self.name = name
    
    def runWhenReady (self, method, *args):
        self.runWhenReadyLock.acquire()
        try:
            if self.ready:
                method(*args)
            else:
                self.readylist.append((method,args))
        finally:
            self.runWhenReadyLock.release()
    
    def onReady (self, proto):
        self.readycon.acquire()
        try:
            self.ready = True
            for method, args in self.readylist:
                method(*args)
            del self.readylist[:]
            self.readycon.notifyAll()
        finally:
            self.readycon.release()

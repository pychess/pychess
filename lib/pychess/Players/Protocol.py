
from gobject import GObject, SIGNAL_RUN_FIRST

from pychess.Utils.Move import Move, parseSAN, parseAN, parseLAN, toSAN, toAN
from pychess.Utils.Move import ParsingError
from pychess.Utils.Cord import Cord
from pychess.Utils.const import *
from pychess.System.SubProcess import SubProcess
from pychess.System.Log import log

class Protocol (GObject):
    
    NORMAL, ANALYZING, INVERSE_ANALYZING = range(3)
    
    __gsignals__ = {
        'move':       (SIGNAL_RUN_FIRST, None, (object,)),
        'analyze':    (SIGNAL_RUN_FIRST, None, (object,)),
        'draw_offer': (SIGNAL_RUN_FIRST, None, ()),
        'resign':     (SIGNAL_RUN_FIRST, None, ()),
        'dead':       (SIGNAL_RUN_FIRST, None, ()),
        'ready':      (SIGNAL_RUN_FIRST, None, ())
    }
    
    def __init__ (self, subprocess, color, protover):
        GObject.__init__(self)
        
        self.color = color
        self.defname = subprocess.defname
        self.protover = protover
        
        self.ready = False
        self.engine = subprocess
        self.connected = True
        self.mode = NORMAL
        
        log.debug(reprColor[color]+"\n", self.defname)
    
    
    def kill (self, reason):
        raise NotImplementedError
    
    def end (self, status, reason):
        raise NotImplementedError
    
    
    def moveNow (self):
        raise NotImplementedError
    
    def pause (self):
        raise NotImplementedError
    
    def resume (self):
        raise NotImplementedError
    
    def setBoard (self, history):
        raise NotImplementedError
    
    
    def move (self, history):
        raise NotImplementedError
    
    def time (self, engine, opponent):
        raise NotImplementedError
    
    
    def offerDraw (self):
        raise NotImplementedError
    
    
    def setPonder (self, b):
        raise NotImplementedError
    
    def setStrength (self, strength):
        raise NotImplementedError
    
    def setTimeControls (self, secs, increment = 0, moves = 0):
        raise NotImplementedError
    
    
    def analyze (self, inverse=False):
        raise NotImplementedError
    
    def canAnalyze (self):
        raise NotImplementedError
    
    def isAnalyzing (self):
        return self.mode != NORMAL
    
    
    def __repr__ (self):
        return self.defname

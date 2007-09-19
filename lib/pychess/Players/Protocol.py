
import sys, os, time
from threading import Condition, Lock

from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE, TYPE_PYOBJECT

from pychess.Utils.Move import Move, parseSAN, parseAN, parseLAN, toSAN, toAN
from pychess.Utils.Move import ParsingError
from pychess.Utils.Cord import Cord
from pychess.Utils.const import *
from pychess.System.SubProcess import SubProcess
from pychess.System.Log import log

class Protocol (GObject):
    
    NORMAL, ANALYZING, INVERSE_ANALYZING = range(3)
    
    __gsignals__ = {
        'move': (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
        'analyze': (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
        'draw_offer': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'resign': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'dead': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'ready': (SIGNAL_RUN_FIRST, TYPE_NONE, ())
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
        pass
    
    def end (self, status, reason):
        pass
    
    
    def moveNow (self):
        pass
    
    def pause (self):
        pass
    
    def resume (self):
        pass
    
    def setBoard (self, history):
        pass
    
    
    def move (self, history):
        pass
    
    def time (self, engine, opponent):
        pass
    
    
    def offerDraw (self):
        pass
    
    
    def setPonder (self, b):
        pass
    
    def setStrength (self, strength):
        pass
    
    def setTimeControls (self, secs, increment = 0, moves = 0):
        pass
    
    
    def analyze (self, inverse=False):
        pass
    
    def canAnalyze (self):
        pass
    
    def isAnalyzing (self):
        return self.mode != NORMAL
    
    
    def __repr__ (self):
        return self.defname

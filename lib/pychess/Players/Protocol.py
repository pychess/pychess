
import sys, os, time
from threading import Condition, Lock
from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE, TYPE_PYOBJECT

from Engine import Engine, EngineConnection
from pychess.Utils.Move import Move, parseSAN, parseAN, parseLAN, toSAN, toAN, ParsingError
from pychess.Utils.Cord import Cord
from pychess.Utils.const import *
from pychess.System.Log import log

# Chess Engine Communication Protocol
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
    
    def __init__ (self, args, color):
        GObject.__init__(self)
        
        self.color = color
        self.executable = args[0]
        defname = os.path.split(self.executable)[1]
        self.defname = defname[:1].upper() + defname[1:].lower()

        self.ready = False
        self.engine = EngineConnection (self.executable)
        self.connected = True
        self.mode = NORMAL
        
        log.debug(reprColor[color]+"\n", self.defname)
        
        def callback (engine):
            if self.connected:
                self.kill()
                if not self.ready:
                    self.ready = True
                    self.emit("ready")
                self.emit('dead')
        self.engine.connect("hungup", callback)
    
    def run (self):
        pass
    
    def kill (self, reason):
        pass
    
    def end (self, status, reason):
        pass
    
    def moveNow (self):
        pass
    
    def move (self, history):
        pass
    
    def pause (self):
        pass
    
    def resume (self):
        pass
    
    def resultWhite (self, comment="White Mates"):
        pass
    
    def resultBlack (self, comment="Black Mates"):
        pass
    
    def resultDraw (self, comment="Draw Game"):
        pass
    
    def time (self, engine, opponent):
        pass
    
    def offerDraw (self):
        pass
    
    def setPonder (self, b):
        pass
    
    def setBoard (self, history):
        pass
    
    def setStrength (self, strength):
        pass
    
    def setTimeControls (self, secs, increment = 0, moves = 0):
        pass
    
    def analyze (self, inverse=False):
        pass
    
    #####
    
    def canAnalyze (self):
        pass
    
    def isAnalyzing (self):
        return self.mode != NORMAL
    
    def __repr__ (self):
        return self.defname

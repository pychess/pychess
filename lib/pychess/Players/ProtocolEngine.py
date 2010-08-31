from gobject import GObject, SIGNAL_RUN_FIRST
from threading import Condition, Lock, RLock

from pychess.System.Log import log
from pychess.Players.Engine import Engine
from pychess.Utils.const import *

class ProtocolEngine (Engine):
    
    __gsignals__ = {
        "readyForOptions": (SIGNAL_RUN_FIRST, None, ()),
        "readyForMoves": (SIGNAL_RUN_FIRST, None, ())
    }
    
    #===========================================================================
    #    Setting engine options
    #===========================================================================
    
    def __init__ (self, subprocess, color, protover):
        Engine.__init__(self)
        
        self.engine = subprocess
        self.defname = subprocess.defname
        self.color = color
        self.protover = protover
        
        self.readyMoves = False
        self.readyOptions = False
        
        self.connected = True
        self.mode = NORMAL
        
        log.debug(reprColor[color]+"\n", self.defname)
        
        self.movecon = Condition()

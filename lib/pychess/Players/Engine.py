
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE

from pychess.Utils.const import ARTIFICIAL
from Player import Player

class Engine (Player):
    
    __type__ = ARTIFICIAL
    
    __gsignals__ = {
        'analyze': (SIGNAL_RUN_FIRST, TYPE_NONE, (object,))
    }
    
    def setStrength (self, strength):
        """ Takes strength 0, 1, 2 (higher is better) """
        abstract
    
    def setDepth (self, depth):
        """ Sets the depth of the engine. Should only be used for analyze engines.
            Other engines will use the setStrength method. """
        pass
    
    def setTime (self, seconds, gain):
        abstract
    
    def setBoard (self, history):
        abstract
    
    def canAnalyze (self):
        abstract
    
    def analyze (self, inverse=False):
        pass #Won't be used if "canAnalyze" responds false
    
    # Other methods
    
    def __repr__ (self):
        """For example 'GNU Chess 5.07'"""
        abstract
    
    def wait (self):
        pass #optional

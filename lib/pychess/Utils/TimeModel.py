from time import time
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, GObject
from pychess.Utils.const import WHITE, BLACK

class TimeModel (GObject):
    
    __gsignals__ = {
        "player_changed": (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        "time_changed": (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        "pause_changed": (SIGNAL_RUN_FIRST, TYPE_NONE, (bool,))
    }
    
    ############################################################################
    # Initing                                                                  #
    ############################################################################
    
    def __init__ (self, secs, gain):
        GObject.__init__(self)
        
        self.intervals = [[secs],[secs]]
        self.gain = gain
        
        self.paused = False
        # The left number of secconds at the time pause was turned on
        self.pauseInterval = 0
        self.counter = None
        
        self.movingColor = None
    
    ############################################################################
    # Interacting                                                              #
    ############################################################################
    
    def setMovingColor (self, movingColor):
        if movingColor == self.movingColor:
            return
        
        if self.paused: return
        
        if self.movingColor != None:
            t = self.intervals[self.movingColor][-1] + self.gain
            if self.counter != None:
                t -= time() - self.counter
            self.intervals[self.movingColor].append(t)
        
        self.counter = time()
        self.movingColor = movingColor
        
        self.emit("time_changed")
        self.emit("player_changed")
        
    def pause (self):
        if self.paused: return
        self.paused = True
        
        if self.counter != None:
            self.pauseInterval = time()-self.counter
        
        self.counter = None
        self.emit("time_changed")
        self.emit("pause_changed", True)
    
    def resume (self):
        if not self.paused: return
        self.paused = False
        self.counter = time() - self.pauseInterval
        
        self.emit("pause_changed", False)
    
    ############################################################################
    # Undo and redo in TimeModel                                               #
    ############################################################################
    
    def undo (self):
        """ Sets time to the amount the current player had last time he started
        his move.
        Example:
        White intervals (is thinking): [120, 130, ...]
        Black intervals:               [120, 115]
        Is undoed to:
        White intervals (is thinking): [120, ...]
        Black intervals:               [120] """
        
        assert not self.paused and \
            len(self.inervals[0]) > 1 and \
            len(self.inervals[1]) > 1
        
        del self.intervals[0][-1]
        del self.intervals[1][-1]
        
        self.counter = time()
        
        self.emit("time_changed")
        self.emit("time_changed")
    
    ############################################################################
    # Updating                                                                 #
    ############################################################################
    
    def updatePlayer (self, color, secs):
        
        
        if color == self.movingColor:
            self.counter = time() - secs
        else: self.intervals[1-self.movingColor][-1] = secs
        self.emit("time_changed")
    
    def syncClock (self, wsecs, bsecs):
        """ Syncronize clock to e.g. fics time """
        if self.movingColor == WHITE:
            self.counter = wsecs + time() - self.intervals[WHITE][-1]
            self.intervals[BLACK][-1] = bsecs
        else:
            self.counter = bsecs + time() - self.intervals[BLACK][-1]
            self.intervals[WHITE][-1] = wsecs
        self.emit("time_changed")
    
    ############################################################################
    # Info                                                                     #
    ############################################################################
    
    def getPlayerTime (self, color):
        
        if color == self.movingColor:
            if self.paused:
                return self.intervals[color][-1] - self.pauseInterval
            return self.intervals[color][-1] - (time() - self.counter)
        return self.intervals[color][-1]
    
    def getInitialTime (self):
        return self.intervals[WHITE][0]

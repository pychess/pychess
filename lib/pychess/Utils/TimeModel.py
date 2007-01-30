from time import time
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, GObject

class TimeModel (GObject):
    
    __gsignals__ = {
        "timed_out": (SIGNAL_RUN_FIRST, TYPE_NONE, (int,)),
        "player_changed": (SIGNAL_RUN_FIRST, TYPE_NONE, (int, int)),
        "time_changed": (SIGNAL_RUN_FIRST, TYPE_NONE, (int,)),
        "pause_changed": (SIGNAL_RUN_FIRST, TYPE_NONE, (bool,))
    }
    
    ############################################################################
    # Initing                                                                  #
    ############################################################################
    
    def __init__ (self, secs, gain):
        self.intervals = [[secs],[secs]]
        self.gain = gain
        
        self.paused = False
        # The left number of secconds at the time pause was turned on
        self.pauseInterval = 0
        self.counter = -1
    
    ############################################################################
    # Interacting                                                              #
    ############################################################################
    
    def setMovingColor (self, movingColor):
        if movingColor == self.movingColor:
            return
        
        if self.counter != -1:
            t = time() - self.counter
        else: t = 0
        t += self.itervals[self.movingColor][-1] + self.gain
        
        self.counter = time()
        
        self.itervals[self.movingColor].append(t)
        self.emit("time_changed", self.movingColor, t)
        self.emit("player_changed", self.movingColor)
    
    def pause (self):
        if self.paused: return
        self.paused = True
        self.pauseInterval = time()-self.counter
        
        self.counter = -1
        self.emit("time_changed", self.movingColor, self.pauseInterval)
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
        
        self.emit("time_changed", 1-self.movingColor,
                                          self.intervals[0][1-self.movingColor])
        self.emit("time_changed", self.movingColor,
                                            self.intervals[0][self.movingColor])
    
    ############################################################################
    # Updating                                                                 #
    ############################################################################
    
    def updatePlayer (self, color, secs):
        """ Syncronize clock to e.g. fics time """
        
        if color == self.movingColor:
            self.counter = time() - secs
        else: self.intervals[1-self.movingColor][-1] = secs
        self.emit("time_changed", color, secs)
        
    def getPlayerTime (self, color):
        if color == self.movingColor:
            return self.intervals[color][-1] - (time() - self.counter)
        return self.intervals[1-color][-1]

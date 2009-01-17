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
    
    def __init__ (self, secs, gain, bsecs=-1):
        GObject.__init__(self)
        
        if bsecs < 0: bsecs = secs
        self.intervals = [[secs],[bsecs]]
        self.gain = gain
        
        self.paused = False
        # The left number of secconds at the time pause was turned on
        self.pauseInterval = 0
        self.counter = None
        
        self.started = False
        self.ended = False
        
        self.movingColor = WHITE
    
    ############################################################################
    # Interacting                                                              #
    ############################################################################
    
    def setMovingColor (self, movingColor):
        self.movingColor = movingColor
        self.emit("player_changed")
    
    def tap (self):
        
        if self.paused: return
        
        if self.started:
            t = self.intervals[self.movingColor][-1] + self.gain
            if self.counter != None:
                t -= time() - self.counter
            self.intervals[self.movingColor].append(t)
        else:
            self.intervals[self.movingColor].append (
                    self.intervals[self.movingColor][-1] )
            
            if len(self.intervals[0]) + len(self.intervals[1]) >= 4:
                self.started = True
        
        self.movingColor = 1-self.movingColor
        
        if self.started:
            self.counter = time()
            self.emit("time_changed")
        
        self.emit("player_changed")
    
    def start (self):
        if self.started: return
        self.started = True
        
        self.counter = time()
        self.emit("time_changed")
    
    def end (self):
        self.pause()
        self.ended = True
    
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
    
    def undoMoves (self, moves):
        """ Sets time and color to move, to the values they were having in the
            beginning of the ply before the current.
        his move.
        Example:
        White intervals (is thinking): [120, 130, ...]
        Black intervals:               [120, 115]
        Is undoed to:
        White intervals:               [120, 130]
        Black intervals (is thinking): [120, ...] """
        
        if not self.started:
            self.start()
        
        for i in xrange(moves):
            self.movingColor = 1-self.movingColor
            del self.intervals[self.movingColor][-1]
        
        if len(self.intervals[0]) + len(self.intervals[1]) >= 4:
            self.counter = time()
        else:
            self.started = False
            self.counter = None
        
        self.emit("time_changed")
        self.emit("player_changed")
    
    ############################################################################
    # Updating                                                                 #
    ############################################################################
    
    def updatePlayer (self, color, secs):
        if color == self.movingColor and self.started:
            self.counter = secs + time() - self.intervals[color][-1]
        else: self.intervals[color][-1] = secs
        self.emit("time_changed")
    
    def syncClock (self, wsecs, bsecs):
        """ Syncronize clock to e.g. fics time """
        if self.movingColor == WHITE:
            if self.started:
                self.counter = wsecs + time() - self.intervals[WHITE][-1]
            else: self.intervals[WHITE][-1] = wsecs
            self.intervals[BLACK][-1] = bsecs
        else:
            if self.started:
                self.counter = bsecs + time() - self.intervals[BLACK][-1]
            else: self.intervals[BLACK][-1] = bsecs
            self.intervals[WHITE][-1] = wsecs
        self.emit("time_changed")
    
    ############################################################################
    # Info                                                                     #
    ############################################################################
    
    def getPlayerTime (self, color):
        if color == self.movingColor and self.started:
            if self.paused:
                return self.intervals[color][-1] - self.pauseInterval
            elif self.counter:
                return self.intervals[color][-1] - (time() - self.counter)
        return self.intervals[color][-1]
    
    def getInitialTime (self):
        return self.intervals[WHITE][0]

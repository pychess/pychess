import heapq
from time import time
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, GObject
from pychess.Utils.const import WHITE, BLACK
from pychess.System import repeat
from pychess.System.Log import log

class TimeModel (GObject):
    
    __gsignals__ = {
        "player_changed": (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        "time_changed": (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        "zero_reached": (SIGNAL_RUN_FIRST, TYPE_NONE, (int,)),
        "pause_changed": (SIGNAL_RUN_FIRST, TYPE_NONE, (bool,))
    }
    
    ############################################################################
    # Initing                                                                  #
    ############################################################################
    
    def __init__ (self, secs, gain, bsecs=-1, minutes=-1):
        GObject.__init__(self)
        
        if bsecs < 0: bsecs = secs
        if minutes < 0:
            minutes = secs / 60
        self.minutes = minutes  # The number of minutes for the original starting
            # time control (not necessarily where the game was resumed,
            # i.e. self.intervals[0][0])
        self.intervals = [[secs],[bsecs]]
        self.gain = gain
        
        self.paused = False
        # The left number of secconds at the time pause was turned on
        self.pauseInterval = 0
        self.counter = None
        
        self.started = False
        self.ended = False
        
        self.movingColor = WHITE
        
        self.connect('time_changed', self.__zerolistener, 'time_changed')
        self.connect('player_changed', self.__zerolistener, 'player_changed')
        self.connect('pause_changed', self.__zerolistener, 'pause_changed')
        self.heap = []
    
    def __repr__ (self):
        s = "<TimeModel object at %s (White: %s Black: %s)>" % \
            (id(self), str(self.getPlayerTime(WHITE)), str(self.getPlayerTime(BLACK)))
        return s
    
    def __zerolistener(self, *args):
        # If we are called by a sleeper (rather than a signal) we need to pop
        # at least one time, as we might otherwise end up with items in the
        # heap, but no sleepers.
        if len(args) == 0 and self.heap:
            self.heap.pop()
        # Pop others (could this give a problem where too many are popped?)
        # No I don't think so. If a sleeper is too slow, so a later sleeper
        # comes before him and pops him, then it is most secure not to rely on
        # mr late, and start a new one.
        # We won't be 'one behind' always, because the previous pop doesnt
        # happen if the heap is empty.
        while self.heap and self.heap[-1] <= time():
            self.heap.pop()
        
        if self.getPlayerTime(WHITE) <= 0:
            #print 'emit for white'
            self.emit('zero_reached', WHITE)
        if self.getPlayerTime(BLACK) <= 0:
            #print 'emit for black'
            self.emit('zero_reached', BLACK)
        
        #print 'heap is now', self.heap
        
        t1 = time() + self.getPlayerTime(WHITE)
        t2 = time() + self.getPlayerTime(BLACK)
        t = min(t1,t2)
        
        if not self.heap or t < self.heap[-1]:
            s = t-time()+0.01
            if s > 0:
                self.heap.append(t)
                # Because of recur, we wont get callback more than once.
                repeat.repeat_sleep(self.__zerolistener, s, recur=True)
                #print 'repeat on', s
    
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
        log.debug("TimeModel.pause: self=%s" % self)
        if self.paused: return
        self.paused = True
        
        if self.counter != None:
            self.pauseInterval = time()-self.counter
        
        self.counter = None
        self.emit("time_changed")
        self.emit("pause_changed", True)
    
    def resume (self):
        log.debug("TimeModel.resume: self=%s" % self)
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

    def getElapsedMoveTime (self, ply):
        movecount, color = divmod(ply+1, 2)
        gain = self.gain if ply > 2 else 0
        if len(self.intervals[color]) > movecount:
            return self.intervals[color][movecount-1] - self.intervals[color][movecount] + gain if movecount > 1 else 0
        else:
            return 0
        
    @property
    def display_text (self):
        t = ("%d " % self.minutes) + _("min")
        if self.gain != 0:
            t += (" + %d " % self.gain) + _("sec")
        return t

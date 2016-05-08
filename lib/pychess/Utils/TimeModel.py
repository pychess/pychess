from time import time

from gi.repository import GLib, GObject

from pychess.Utils.const import WHITE, BLACK
from pychess.System.Log import log


class TimeModel(GObject.GObject):

    __gsignals__ = {
        "player_changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "time_changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "zero_reached": (GObject.SignalFlags.RUN_FIRST, None, (int, )),
        "pause_changed": (GObject.SignalFlags.RUN_FIRST, None, (bool, ))
    }

    ############################################################################
    # Initing                                                                  #
    ############################################################################

    def __init__(self, secs=0, gain=0, bsecs=-1, minutes=-1):
        GObject.GObject.__init__(self)
        if bsecs < 0:
            bsecs = secs
        if minutes < 0:
            minutes = secs / 60
        self.minutes = minutes  # The number of minutes for the original starting
        # time control (not necessarily where the game was resumed,
        # i.e. self.intervals[0][0])
        self.intervals = [[secs], [bsecs]]
        self.gain = gain
        self.secs = secs

        # in FICS games we don't count gain
        self.handle_gain = True

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

        self.zero_listener_id = None
        self.zero_listener_time = 0
        self.zero_listener_source = None

    def __repr__(self):
        text = "<TimeModel object at %s (White: %s Black: %s ended=%s)>" % \
            (id(self), str(self.getPlayerTime(WHITE)),
             str(self.getPlayerTime(BLACK)), self.ended)
        return text

    def __zerolistener(self, *args):
        if self.ended:
            return False

        cur_time = time()
        whites_time = cur_time + self.getPlayerTime(WHITE)
        blacks_time = cur_time + self.getPlayerTime(BLACK)
        if whites_time <= blacks_time:
            the_time = whites_time
            color = WHITE
        else:
            the_time = blacks_time
            color = BLACK

        remaining_time = the_time - cur_time + 0.01
        if remaining_time > 0 and remaining_time != self.zero_listener_time:
            if (self.zero_listener_id is not None) and \
                (self.zero_listener_source is not None) and \
                    not self.zero_listener_source.is_destroyed():
                GLib.source_remove(self.zero_listener_id)
            self.zero_listener_time = remaining_time
            self.zero_listener_id = GLib.timeout_add(10, self.__checkzero,
                                                     color)
            default_context = GLib.main_context_get_thread_default(
            ) or GLib.main_context_default()
            if hasattr(default_context, "find_source_by_id"):
                self.zero_listener_source = default_context.find_source_by_id(
                    self.zero_listener_id)

    def __checkzero(self, color):
        if self.getPlayerTime(color) <= 0 and self.started:
            self.emit('zero_reached', color)
            return False
        return True

        ############################################################################
        # Interacting                                                              #
        ############################################################################

    def setMovingColor(self, movingColor):
        self.movingColor = movingColor
        self.emit("player_changed")

    def tap(self):
        if self.paused:
            return

        gain = self.gain if self.handle_gain else 0
        ticker = self.intervals[self.movingColor][-1] + gain
        if self.started:
            if self.counter is not None:
                ticker -= time() - self.counter
        else:
            # FICS rule
            if self.ply >= 1:
                self.started = True
        self.intervals[self.movingColor].append(ticker)

        self.movingColor = 1 - self.movingColor

        if self.started:
            self.counter = time()
            self.emit("time_changed")

        self.emit("player_changed")

    def start(self):
        if self.started:
            return
        self.counter = time()
        self.emit("time_changed")

    def end(self):
        log.debug("TimeModel.end: self=%s" % self)
        self.pause()
        self.ended = True
        if (self.zero_listener_id is not None) and \
            (self.zero_listener_source is not None) and \
                not self.zero_listener_source.is_destroyed():
            GLib.source_remove(self.zero_listener_id)

    def pause(self):
        log.debug("TimeModel.pause: self=%s" % self)
        if self.paused:
            return
        self.paused = True

        if self.counter is not None:
            self.pauseInterval = time() - self.counter

        self.counter = None
        self.emit("time_changed")
        self.emit("pause_changed", True)

    def resume(self):
        log.debug("TimeModel.resume: self=%s" % self)
        if not self.paused:
            return

        self.paused = False
        self.counter = time() - self.pauseInterval

        self.emit("pause_changed", False)

    ############################################################################
    # Undo and redo in TimeModel                                               #
    ############################################################################

    def undoMoves(self, moves):
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

        for move in range(moves):
            self.movingColor = 1 - self.movingColor
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

    def updatePlayer(self, color, secs):
        self.intervals[color][-1] = secs
        if color == self.movingColor and self.started:
            self.counter = secs + time() - self.intervals[color][-1]
        self.emit("time_changed")

    ############################################################################
    # Info                                                                     #
    ############################################################################

    def getPlayerTime(self, color, movecount=-1):
        if color == self.movingColor and self.started and movecount == -1:
            if self.paused:
                return self.intervals[color][movecount] - self.pauseInterval
            elif self.counter:
                return self.intervals[color][movecount] - (time() -
                                                           self.counter)
        return self.intervals[color][movecount]

    def getInitialTime(self):
        return self.intervals[WHITE][0]

    def getElapsedMoveTime(self, ply):
        movecount, color = divmod(ply + 1, 2)
        gain = self.gain if ply > 2 else 0
        if len(self.intervals[color]) > movecount:
            return self.intervals[color][movecount - 1] - self.intervals[
                color][movecount] + gain if movecount > 1 else 0
        else:
            return 0

    @property
    def display_text(self):
        text = ("%d " % self.minutes) + _("min")
        if self.gain != 0:
            text += (" + %d " % self.gain) + _("sec")
        return text

    @property
    def hasTimes(self):
        return len(self.intervals[0]) > 1

    @property
    def ply(self):
        return len(self.intervals[BLACK]) + len(self.intervals[WHITE]) - 2

    def hasBWTimes(self, bmovecount, wmovecount):
        return len(self.intervals[BLACK]) > bmovecount and len(self.intervals[
            WHITE]) > wmovecount

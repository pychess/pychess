from math import ceil
from time import time

from gi.repository import GLib, GObject

from pychess.Utils.const import WHITE, BLACK
from pychess.System.Log import log

# Shortest interval we ever arm the zero listener for. Anything below this is
# pointless: it would burn the main loop without making the flag fall any
# earlier, since GTK cannot repaint faster than this anyway.
MIN_ZERO_LISTENER_INTERVAL_MS = 10


class TimeModel(GObject.GObject):
    __gsignals__ = {
        "player_changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "time_changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "zero_reached": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "pause_changed": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
    }

    ############################################################################
    # Initing                                                                  #
    ############################################################################

    def __init__(
        self,
        secs=0,
        gain=0,
        bsecs=-1,
        minutes=-1,
        moves=0,
        wgain=-1,
        wmoves=-1,
        bgain=-1,
        bmoves=-1,
    ):
        GObject.GObject.__init__(self)
        if bsecs < 0:
            bsecs = secs
        if minutes < 0:
            minutes = secs / 60

        # Handle asymmetric time controls
        if wgain < 0:
            wgain = gain
        if wmoves < 0:
            wmoves = moves
        if bgain < 0:
            bgain = gain
        if bmoves < 0:
            bmoves = moves

        self.minutes = minutes  # The number of minutes for the original starting
        self.moves = moves
        self.wmoves = wmoves
        self.bmoves = bmoves

        # time control (not necessarily where the game was resumed,
        # i.e. self.intervals[0][0])
        if secs == 0 and gain > 0:
            self.intervals = [[wgain], [bgain]]
        else:
            self.intervals = [[secs], [bsecs]]
        self.gain = gain
        self.wgain = wgain
        self.bgain = bgain
        self.secs = secs

        # to know if game is played on ICS or not
        self.gamemodel = None

        # in FICS games we don't count gain
        self.handle_gain = True

        self.paused = False
        # The left number of secconds at the time pause was turned on
        self.pauseInterval = 0
        self.counter = None

        self.started = False
        self.ended = False

        self.movingColor = WHITE

        self.connect("time_changed", self.__zerolistener, "time_changed")
        self.connect("player_changed", self.__zerolistener, "player_changed")
        self.connect("pause_changed", self.__zerolistener, "pause_changed")

        # Each arming of the zero listener carries a generation number. A
        # callback holding a stale generation belongs to a timeout that has
        # been superseded, so it must not emit or re-arm anything.
        self.zero_listener_id = None
        self.zero_listener_generation = 0
        # Color we already reported as running out of time. It is cleared as
        # soon as that player gets time back, so the flag is announced once.
        self.zero_reached_color = None

    def __repr__(self):
        text = f"<TimeModel object at {id(self)} (White: {str(self.getPlayerTime(WHITE))} Black: {str(self.getPlayerTime(BLACK))} ended={self.ended})>"
        return text

    def __remove_zero_listener(self):
        """Cancel the pending flag check, if any.

        Bumping the generation first makes any callback that is already queued
        a no-op, so we never depend on being able to resolve the GLib source.
        """
        self.zero_listener_generation += 1
        source_id = self.zero_listener_id
        self.zero_listener_id = None
        if source_id is not None:
            GLib.source_remove(source_id)

    def __arm_zero_listener(self, color, remaining_time):
        interval_ms = max(
            MIN_ZERO_LISTENER_INTERVAL_MS, int(ceil(remaining_time * 1000))
        )
        self.zero_listener_generation += 1
        generation = self.zero_listener_generation
        self.zero_listener_id = GLib.timeout_add(
            interval_ms, self.__checkzero, color, generation
        )

    def __zerolistener(self, *args):
        if self.ended:
            return False

        if not self.started or self.paused:
            # A clock that has not started yet, or that is paused, does not
            # count down, so nothing can expire. Drop any pending check;
            # start(), resume() and tap() each emit a signal that re-arms it.
            self.__remove_zero_listener()
            return False

        cur_time = time()
        whites_time = cur_time + self.getPlayerTime(WHITE)
        blacks_time = cur_time + self.getPlayerTime(BLACK)
        if self.movingColor == WHITE:
            the_time = whites_time
            color = WHITE
        else:
            the_time = blacks_time
            color = BLACK

        remaining_time = the_time - cur_time + 0.01
        if remaining_time > 0:
            # More than the rounding slack means this player really has time
            # again, so a later flag has to be announced once more. Without
            # this, a flag callback would stay suppressed forever once fired.
            if remaining_time > MIN_ZERO_LISTENER_INTERVAL_MS / 1000.0:
                self.zero_reached_color = None
            # Arm exactly one timeout for the moment the player is expected to
            # run out of time. Re-checking every few milliseconds instead would
            # wake the GLib main loop ~100 times per second for the whole
            # duration of a move, doing nothing.
            self.__remove_zero_listener()
            self.__arm_zero_listener(color, remaining_time)

    def __checkzero(self, color, generation):
        if generation != self.zero_listener_generation:
            # Superseded by a newer arming; that one is the live check.
            return False

        # This source has just expired, so it must no longer be removed.
        self.zero_listener_id = None

        if self.getPlayerTime(color) <= 0 and self.started:
            if self.zero_reached_color != color:
                self.zero_reached_color = color
                self.emit("time_changed")
                self.emit("zero_reached", color)
            return False

        # Millisecond rounding can fire us marginally early. Re-arm for the
        # little that is left rather than dropping the check entirely.
        self.__zerolistener()
        return False

    ############################################################################
    # Interacting                                                              #
    ############################################################################

    def setMovingColor(self, movingColor):
        self.movingColor = movingColor
        self.emit("player_changed")

    def tap(self):
        if self.paused:
            return

        # Use player-specific gains for asymmetric time controls
        if self.movingColor == WHITE:
            gain = self.wgain if self.handle_gain else 0
            moves = self.wmoves
        else:
            gain = self.bgain if self.handle_gain else 0
            moves = self.bmoves
        ticker = self.intervals[self.movingColor][-1] + gain
        if self.started:
            if self.counter is not None:
                ticker -= time() - self.counter
        else:
            # FICS rule
            if self.gamemodel.isPlayingICSGame():
                if self.ply >= 1:
                    self.started = True
            else:
                self.started = True
        if moves == 0:
            self.intervals[self.movingColor].append(ticker)
        else:
            if len(self.intervals[self.movingColor]) % moves == 0:
                self.intervals[self.movingColor].append(
                    self.intervals[self.movingColor][0]
                )
            else:
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
        self.__remove_zero_listener()

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
        """Sets time and color to move, to the values they were having in the
            beginning of the ply before the current.
        his move.
        Example:
        White intervals (is thinking): [120, 130, ...]
        Black intervals:               [120, 115]
        Is undoed to:
        White intervals:               [120, 130]
        Black intervals (is thinking): [120, ...]"""

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
                return max(0, self.intervals[color][movecount] - self.pauseInterval)
            elif self.counter:
                return max(
                    0, self.intervals[color][movecount] - (time() - self.counter)
                )
        return max(0, self.intervals[color][movecount])

    def getInitialTime(self):
        return self.intervals[WHITE][0]

    def getElapsedMoveTime(self, ply):
        movecount, color = divmod(ply + 1, 2)
        gain = self.gain if ply > 2 else 0
        if len(self.intervals[color]) > movecount:
            return (
                self.intervals[color][movecount - 1]
                - self.intervals[color][movecount]
                + gain
            )
        else:
            return 0

    @property
    def display_text(self):
        if self.isAsymmetric:
            # For asymmetric time controls, show both players' time
            white_mins = self.intervals[WHITE][0] / 60
            black_mins = self.intervals[BLACK][0] / 60
            text = _("White: %d min") % white_mins
            if self.wgain != 0:
                text += (" + %d " % self.wgain) + _("sec")
            text += _(", Black: %d min") % black_mins
            if self.bgain != 0:
                text += (" + %d " % self.bgain) + _("sec")
            return text
        else:
            # Symmetric time controls
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
        return (
            len(self.intervals[BLACK]) > bmovecount
            and len(self.intervals[WHITE]) > wmovecount
        )

    def isBlitzFide(self):
        val = 60 * self.minutes + 60 * (self.gain if self.handle_gain else 0)
        return (
            val > 0 and val <= 600
        )  # Less or equal than 10 minutes for 60 moves and for each player

    @property
    def isAsymmetric(self):
        """Check if different time controls are used for white and black players"""
        return (
            self.intervals[WHITE][0] != self.intervals[BLACK][0]
            or self.wgain != self.bgain
            or self.wmoves != self.bmoves
        )

    def getPlayerGain(self, color):
        """Get the gain for a specific player"""
        return self.wgain if color == WHITE else self.bgain

    def getPlayerMoves(self, color):
        """Get the moves for a specific player"""
        return self.wmoves if color == WHITE else self.bmoves

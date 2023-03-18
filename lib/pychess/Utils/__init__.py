import asyncio
import weakref
from math import ceil

from pychess.Utils.lutils.ldata import MATE_VALUE, MATE_DEPTH


def formatTime(seconds, clk2pgn=False):
    minus = ""
    if seconds <= -10 or seconds >= 10:
        seconds = ceil(seconds)
    if seconds < 0:
        minus = "-"
        seconds = -seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours or clk2pgn:
        return minus + "%d:%02d:%02d" % (hours, minutes, seconds)
    elif not minutes and seconds < 10:
        return minus + "%.1f" % seconds
    else:
        return minus + "%d:%02d" % (minutes, seconds)


def prettyPrintScore(s, depth, format_mate=False):
    """The score parameter is an eval value from White point of view"""

    # Particular values
    if s is None:
        return "?"
    if s == -MATE_VALUE:
        return _("Illegal")
    if s == 0:
        return "0.00/%s" % depth

    # Preparation
    if s > 0:
        pp = "+"
        mp = ""
    else:
        pp = "-"
        mp = "-"
        s = -s
    if depth:
        depth = "/" + depth
    else:
        depth = ""

    # Rendering
    if s < MATE_VALUE - MATE_DEPTH:
        return f"{pp}{s / 100.0:0.2f}{depth}"
    else:
        mate_in = int(MATE_VALUE - s)
        if format_mate:
            if mate_in == 0:
                return _("Mate")
            return "%s #%s%d" % (_("Mate"), mp, mate_in)
        else:
            return f"{pp}#{s:.0f}"  # Sign before sharp to be parsed in PGN


def createStoryTextAppEvent(text):
    try:
        import storytext

        storytext.applicationEvent(text)
    except AttributeError:
        pass
    except ImportError:
        pass


class wait_signal(asyncio.Future):
    """A future for waiting for a given signal to occur."""

    def __init__(self, obj, name, *, loop=None):
        super().__init__(loop=loop)
        self._obj = weakref.ref(obj, lambda s: self.cancel())
        self._hnd = obj.connect(name, self._signal_callback)

    def _signal_callback(self, *k):
        obj = self._obj()
        if obj is not None:
            obj.disconnect(self._hnd)
        self.set_result(k)

    def cancel(self, msg=None):
        if self.cancelled():
            return False
        try:
            super().cancel(msg=msg)
        except TypeError:  # It has msg parameter only form Python 3.9
            super().cancel()
        except AttributeError:
            pass
        try:
            obj = self._obj()
            if obj is not None:
                obj.disconnect(self._hnd)
        except AttributeError:
            pass
        return True

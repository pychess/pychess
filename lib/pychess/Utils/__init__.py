import asyncio
import weakref

from pychess.Utils.lutils.ldata import MATE_VALUE, MATE_DEPTH


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
        return "%s%0.2f%s" % (pp, s / 100.0, depth)
    else:
        mate_in = int(MATE_VALUE - s)
        if format_mate:
            if mate_in == 0:
                return _("Mate")
            return "%s #%s%d" % (_("Mate"), mp, mate_in)
        else:
            return "%s#%.0f" % (pp, s)  # Sign before sharp to be parsed in PGN


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

    def cancel(self):
        if self.cancelled():
            return False
        try:
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

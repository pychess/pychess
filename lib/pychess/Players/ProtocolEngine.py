from gi.repository import GObject

from pychess.Players.Engine import Engine
from pychess.Utils.const import NORMAL, ANALYZING, INVERSE_ANALYZING

TIME_OUT_SECOND = 60


class ProtocolEngine(Engine):

    __gsignals__ = {
        "readyForOptions": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "readyForMoves": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    # Setting engine options

    def __init__(self, subprocess, color, protover, md5):
        Engine.__init__(self, md5)

        self.engine = subprocess
        self.defname = subprocess.defname
        self.color = color
        self.protover = protover

        self.readyMoves = False
        self.readyOptions = False

        self.connected = True
        self.mode = NORMAL
        self.analyzing_paused = False

    def isAnalyzing(self):
        return self.mode in (ANALYZING, INVERSE_ANALYZING)

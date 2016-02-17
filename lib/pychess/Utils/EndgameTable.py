from __future__ import absolute_import
from gi.repository import GObject

from .Move import Move
from .lutils.egtb_k4it import EgtbK4kit
from .lutils.egtb_gaviota import EgtbGaviota

providers = []


class EndgameTable(GObject.GObject):
    """ Wrap the low-level providers of exact endgame knowledge. """

    __gsignals__ = {
        "scored": (GObject.SignalFlags.RUN_FIRST, None, (object, )),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        global providers
        if not providers:
            providers = [EgtbGaviota(), EgtbK4kit()]
        self.providers = providers

    def _pieceCounts(self, board):
        return sorted([bin(board.friends[i]).count("1") for i in range(2)])

    def scoreGame(self, lBoard, omitDepth=False, probeSoft=False):
        """ Return result and depth to mate. (Intended for engine use.)

            lBoard: A low-level board structure
            omitDepth: Look up only the game's outcome (may save time)
            probeSoft: Fail if the probe would require disk or network access.
            Return value:
            game_result: Either WHITEWON, DRAW, BLACKWON, or (on failure) None
            depth: Depth to mate, or (if omitDepth or the game is drawn) None
        """

        piece_count = self._pieceCounts(lBoard)
        for provider in self.providers:
            if provider.supports(piece_count):
                result, depth = provider.scoreGame(lBoard, omitDepth,
                                                   probeSoft)
                if result is not None:
                    return result, depth
        return None, None

    def scoreAllMoves(self, lBoard):
        """ Return each move's result and depth to mate.

            lBoard: A low-level board structure
            Return value: a list, with best moves first, of:
            move: A high-level move structure
            game_result: Either WHITEWON, DRAW, BLACKWON
            depth: Depth to mate
        """

        piece_count = self._pieceCounts(lBoard)
        for provider in self.providers:
            if provider.supports(piece_count):
                results = provider.scoreAllMoves(lBoard)
                if results:
                    ret = []
                    for lmove, result, depth in results:
                        ret.append((Move(lmove), result, depth))
                    self.emit("scored", (lBoard, ret))
                    return ret
        return []

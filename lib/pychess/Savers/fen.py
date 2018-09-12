import collections
from io import StringIO

from pychess.Utils.GameModel import GameModel
from pychess.Utils.const import WAITING_TO_START, BLACKWON, WHITEWON, DRAW, FISCHERRANDOMCHESS
from pychess.Utils.logic import getStatus
from pychess.Variants.fischerandom import FischerandomBoard

from .ChessFile import ChessFile, LoadingError


__label__ = _("Simple Chess Position")
__ending__ = "fen"
__append__ = True


def save(handle, model, position=None, flip=False):
    """Saves game to file in fen format"""
    print(position, model.ply, model.lowply)
    print(model.boards)
    print("%s" % model.boards[-1 if position is None or len(model.boards) == 1 else position].asFen(),
          file=handle)
    output = handle.getvalue() if isinstance(handle, StringIO) else ""
    handle.close()
    return output


def load(handle):
    return FenFile(handle)


class FenFile(ChessFile):
    def __init__(self, handle):
        ChessFile.__init__(self, handle)
        self.fen_is_string = isinstance(handle, StringIO)
        rec = collections.defaultdict(str)
        line = handle.readline().strip()
        rec["Id"] = 0
        rec["Offset"] = 0
        rec["FEN"] = line

        castling = rec["FEN"].split()[2]
        for letter in castling:
            if letter.upper() in "ABCDEFGH":
                rec["Variant"] = FISCHERRANDOMCHESS
                break

        self.games = [rec, ]
        self.count = 1

    def loadToModel(self, rec, position, model=None):
        if not model:
            model = GameModel()

        if self.fen_is_string:
            rec = self.games[0]

        if isinstance(rec, dict) and "Variant" in rec:
            model.variant = FischerandomBoard

        fen = self.games[0]["FEN"]
        try:
            board = model.variant(setup=fen)
            model.tags["FEN"] = fen
        except SyntaxError as err:
            board = model.variant()
            raise LoadingError(
                _("The game can't be loaded, because of an error parsing FEN"),
                err.args[0])

        model.boards = [board]
        model.variations = [model.boards]
        model.moves = []
        if model.status == WAITING_TO_START:
            status, reason = getStatus(model.boards[-1])
            if status in (BLACKWON, WHITEWON, DRAW):
                model.status, model.reason = status, reason
        return model

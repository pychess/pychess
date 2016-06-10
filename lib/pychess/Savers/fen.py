from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from pychess.compat import StringIO
from pychess.Utils.GameModel import GameModel
from pychess.Utils.const import WAITING_TO_START, BLACKWON, WHITEWON, DRAW
from pychess.Utils.logic import getStatus

from .ChessFile import ChessFile, LoadingError


__label__ = _("Simple Chess Position")
__ending__ = "fen"
__append__ = True


def save(file, model, position=None):
    """Saves game to file in fen format"""

    print("%s" % model.boards[-1 if position is None or len(model.boards) == 1 else position].asFen(),
          file=file)
    output = file.getvalue() if isinstance(file, StringIO) else ""
    file.close()
    return output


def load(file):
    return FenFile([line.strip() for line in file if line])


class FenFile(ChessFile):
    def loadToModel(self, gameno, position, model=None):
        if not model:
            model = GameModel()

        # We have to set full move number to 1 to make sure LBoard and GameModel
        # are synchronized.
        # fenlist = self.games[gameno].split(" ")
        # if len(fenlist) == 6:
        #    fen = " ".join(fenlist[:5]) + " 1"
        fen = self.games[gameno]
        try:
            board = model.variant(setup=fen)
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

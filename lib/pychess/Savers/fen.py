from __future__ import absolute_import
from __future__ import print_function
from pychess.Utils.GameModel import GameModel
from pychess.Utils.const import WAITING_TO_START, BLACKWON, WHITEWON, DRAW
from pychess.Utils.logic import getStatus

from .ChessFile import LoadingError

__label__ = _("Simple Chess Position")
__ending__ = "fen"
__append__ = True

def save (file, model, position=None):
    """Saves game to file in fen format"""
    
    print(model.boards[-1].asFen(), file=file)
    file.close()
    
def load (file):
    return FenFile ([line for line in map(str.strip, file) if line])

from .ChessFile import ChessFile

class FenFile (ChessFile):
    
    def loadToModel (self, gameno, position, model=None):
        if not model: model = GameModel()
        
        # We have to set full move number to 1 to make sure LBoard and GameModel
        # are synchronized.
        #fenlist = self.games[gameno].split(" ")
        #if len(fenlist) == 6:
        #    fen = " ".join(fenlist[:5]) + " 1" 
        fen = self.games[gameno]
        try:
            board = model.variant.board(setup=fen)
        except SyntaxError as e:
            board = model.variant.board()
            raise LoadingError(_("The game can't be loaded, because of an error parsing FEN"), e.args[0])
        
        model.boards = [board]
        model.variations = [model.boards]
        if model.status == WAITING_TO_START:
            status, reason = getStatus(model.boards[-1])
            if status in (BLACKWON, WHITEWON, DRAW):
                model.status, model.reason = status, reason
        return model

from pychess.Utils.Cord import Cord
from pychess.Utils.Board import Board
from pychess.Utils.Piece import Piece
from pychess.Utils.Move import Move
from pychess.Utils.const import *
from pychess.Utils.logic import getStatus

__label__ = _("Simple Chess Position")
__endings__ = "fen",
__append__ = True

def save (file, model):
    """Saves game to file in fen format"""
    
    print >> file, model.boards[-1].asFen()
    file.close()
    
def load (file):
    return FenFile ([line for line in map(str.strip, file) if line])

from ChessFile import ChessFile

class FenFile (ChessFile):
    
    def loadToModel (self, gameno, position, model=None):
        if not model: model = GameModel()
        
        # We have to set full move number to 1 to make sure LBoard and GameModel
        # are synchronized.
        #fenlist = self.games[gameno].split(" ")
        #if len(fenlist) == 6:
        #    fen = " ".join(fenlist[:5]) + " 1" 
        fen = self.games[gameno]
        
        model.boards = [model.variant.board(setup=fen)]
        if model.status == WAITING_TO_START:
            model.status, model.reason = getStatus(model.boards[-1])
        
        return model

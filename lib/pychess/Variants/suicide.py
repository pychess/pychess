from __future__ import print_function
# Suicide Chess

from pychess.Utils.const import *
from pychess.Utils.Board import Board

SUICIDESTART = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1"

class SuicideBoard(Board):
    variant = SUICIDECHESS

    def __init__ (self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=SUICIDESTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

class SuicideChess:
    __desc__ = _("FICS suicide: http://www.freechess.org/Help/HelpFiles/suicide_chess.html")
    name = _("Suicide")
    cecp_name = "suicide"
    board = SuicideBoard
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD

def pieceCount(board, color):
    return bin(board.friends[color]).count("1")

if __name__ == '__main__':
    from pychess.Utils.Move import Move
    from pychess.Utils.lutils.lmove import parseAN
    from pychess.Utils.lutils.lmovegen import genCaptures

    FEN = "rnbqk1nr/pppp1pPp/4p3/8/8/8/PPPbPPP1/RNBQKBNR b - - 7 4"
    b = SuicideBoard(SUICIDESTART)
    
    b = b.move(Move(parseAN(b.board, "h2h4")))
    print(b.board.__repr__())
    for move in genCaptures(b.board):
        print(Move(move))

    b = b.move(Move(parseAN(b.board, "e7e6")))
    print(b.board.__repr__())
    for move in genCaptures(b.board):
        print(Move(move))

    b = b.move(Move(parseAN(b.board, "h4h5")))
    print(b.board.__repr__())
    for move in genCaptures(b.board):
        print(Move(move))

    b = b.move(Move(parseAN(b.board, "f8b4")))
    print(b.board.__repr__())
    for move in genCaptures(b.board):
        print(Move(move))

    b = b.move(Move(parseAN(b.board, "h5h6")))
    print(b.board.__repr__())
    for move in genCaptures(b.board):
        print(Move(move))

    b = b.move(Move(parseAN(b.board, "b4d2")))
    print(b.board.__repr__())
    for move in genCaptures(b.board):
        print(Move(move))

    b = b.move(Move(parseAN(b.board, "h6g7")))
    print(b.board.__repr__())
    for move in genCaptures(b.board):
        print(Move(move))

    b = b.move(Move(parseAN(b.board, "d2e1")))
    print(b.board.__repr__())
    for move in genCaptures(b.board):
        print(Move(move))


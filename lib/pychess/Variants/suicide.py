# Suicide Chess

from pychess.Utils.const import *
from pychess.Utils.Board import Board

SUICIDESTART = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1"

class SuicideBoard(Board):
    variant = SUICIDECHESS

    def __init__ (self, setup=False):
        if setup is True:
            Board.__init__(self, setup=SUICIDESTART)
        else:
            Board.__init__(self, setup=setup)

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

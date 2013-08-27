# Pawns Pushed Chess

from pychess.Utils.const import *
from pychess.Utils.Board import Board

PAWNSPUSHEDSTART = "rnbqkbnr/8/8/pppppppp/PPPPPPPP/8/8/RNBQKBNR w - - 0 1"

class PawnsPushedBoard(Board):
    variant = PAWNSPUSHEDCHESS

    def __init__ (self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=PAWNSPUSHEDSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)


class PawnsPushedChess:
    __desc__ = _("FICS wild/8: http://www.freechess.org/Help/HelpFiles/wild.html\n" +
                 "Pawns start on 4th and 5th ranks rather than 2nd and 7th")
    name = _("Pawns Pushed")
    cecp_name = "normal"
    board = PawnsPushedBoard
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_OTHER

from pychess.Utils.const import *
from pychess.Utils.Board import Board

ROOKODDSSTART = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/1NBQKBNR w Kkq - 0 1"

class RookOddsBoard(Board):
    variant = ROOKODDSCHESS

    def __init__ (self, setup=False):
        if setup is True:
            Board.__init__(self, setup=ROOKODDSSTART)
        else:
            Board.__init__(self, setup=setup)


class RookOddsChess:
    __desc__ = _("One player starts with one less rook piece")
    name = _("Rook odds")
    cecp_name = "normal"
    board = RookOddsBoard
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_ODDS

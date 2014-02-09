from pychess.Utils.const import *
from pychess.Utils.Board import Board

KNIGHTODDSSTART = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/R1BQKBNR w KQkq - 0 1"

class KnightOddsBoard(Board):
    variant = KNIGHTODDSCHESS

    def __init__ (self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=KNIGHTODDSSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)


class KnightOddsChess:
    __desc__ = _("One player starts with one less knight piece")
    name = _("Knight odds")
    cecp_name = "normal"
    board = KnightOddsBoard
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_ODDS


from pychess.Utils.const import *
from pychess.Utils.Board import Board

KNIGHTODDSSTART = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/R1BQKBNR w KQkq - 0 1"

class KnightOddsBoard(Board):
    variant = KNIGHTODDSCHESS

    def __init__ (self, setup=False):
        if setup is True:
            Board.__init__(self, setup=KNIGHTODDSSTART)
        else:
            Board.__init__(self, setup=setup)


class KnightOddsChess:
    name = _("Knight odds")
    cecp_name = "normal"
    board = KnightOddsBoard
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_ODDS


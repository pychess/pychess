from pychess.Utils.const import *
from pychess.Utils.Board import Board

QUEENODDSSTART = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1"

class QueenOddsBoard(Board):
    variant = QUEENODDSCHESS

    def __init__ (self, setup=False):
        if setup is True:
            Board.__init__(self, setup=QUEENODDSSTART)
        else:
            Board.__init__(self, setup=setup)


class QueenOddsChess:
    name = _("Queen odds")
    cecp_name = "normal"
    board = QueenOddsBoard
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_ODDS


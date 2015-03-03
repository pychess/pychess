from pychess.Utils.const import *
from pychess.Utils.Board import Board

QUEENODDSSTART = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1"

class QueenOddsBoard(Board):
    variant = QUEENODDSCHESS
    __desc__ = _("One player starts with one less queen piece")
    name = _("Queen odds")
    cecp_name = "normal"
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_ODDS

    def __init__ (self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=QUEENODDSSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

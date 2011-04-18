from pychess.Utils.const import *
from pychess.Utils.Board import Board

PAWNODDSSTART = "rnbqkbnr/ppppp1pp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

class PawnOddsBoard(Board):
    variant = PAWNODDSCHESS

    def __init__ (self, setup=False):
        if setup is True:
            Board.__init__(self, setup=PAWNODDSSTART)
        else:
            Board.__init__(self, setup=setup)


class PawnOddsChess:
    __desc__ = _("One player starts with one less pawn piece")
    name = _("Pawn odds")
    cecp_name = "normal"
    board = PawnOddsBoard
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_ODDS


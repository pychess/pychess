# S-Chess

from pychess.Utils.const import (
    SCHESS,
    VARIANTS_OTHER_NONSTANDARD,
    KNIGHT_PROMOTION,
    BISHOP_PROMOTION,
    ROOK_PROMOTION,
    QUEEN_PROMOTION,
    HAWK_PROMOTION,
    ELEPHANT_PROMOTION,
)
from pychess.Utils.Board import Board

SCHESSSTART = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR[heHE] w KQBCDFGkqbcdfg - 0 1"


class SchessBoard(Board):
    variant = SCHESS
    __desc__ = _("S-Chess: https://en.wikipedia.org/wiki/Seirawan_chess")
    name = _("S-Chess")
    cecp_name = "seirawan"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD
    PROMOTIONS = (
        KNIGHT_PROMOTION,
        BISHOP_PROMOTION,
        ROOK_PROMOTION,
        QUEEN_PROMOTION,
        HAWK_PROMOTION,
        ELEPHANT_PROMOTION,
    )

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=SCHESSSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

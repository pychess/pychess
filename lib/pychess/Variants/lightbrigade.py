""" Light Brigade Chess Variant """

from pychess.Utils.const import (
    QUEEN_PROMOTION,
    KNIGHT_PROMOTION,
    LIGHTBRIGADECHESS,
    VARIANTS_OTHER_NONSTANDARD,
)
from pychess.Utils.Board import Board

LIGHTBRIGADESTART = "nnnnknnn/pppppppp/8/8/8/8/PPPPPPPP/1Q1QK1Q1 w - - 0 1"


class LightbrigadeBoard(Board):
    variant = LIGHTBRIGADECHESS
    __desc__ = _(
        "Variant explained at https://www.chessvariants.com/rules/charge-of-the-light-brigade"
    )
    name = _("Charge of the light brigade")
    cecp_name = "light-brigade"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD

    PROMOTIONS = (QUEEN_PROMOTION, KNIGHT_PROMOTION)

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=LIGHTBRIGADESTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

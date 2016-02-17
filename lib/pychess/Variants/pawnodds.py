""" Pawn Odds Variant"""
from pychess.Utils.const import PAWNODDSCHESS, VARIANTS_ODDS
from pychess.Utils.Board import Board

PAWNODDSSTART = "rnbqkbnr/ppppp1pp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


class PawnOddsBoard(Board):
    """:Description: A standard chess game where one  side starts with one less
        pawn, this is known as giving pawn odds
    """
    variant = PAWNODDSCHESS
    __desc__ = _("One player starts with one less pawn piece")
    name = _("Pawn odds")
    cecp_name = "normal"
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_ODDS

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=PAWNODDSSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

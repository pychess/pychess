""" Knightodds variant """
from pychess.Utils.const import KNIGHTODDSCHESS, VARIANTS_ODDS
from pychess.Utils.Board import Board

KNIGHTODDSSTART = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/R1BQKBNR w KQkq - 0 1"


class KnightOddsBoard(Board):
    """:Description: Knight Odds variant plays with the same rules as normal chess
        but one side start the game with a knight missing
    """
    variant = KNIGHTODDSCHESS
    __desc__ = _("One player starts with one less knight piece")
    name = _("Knight odds")
    cecp_name = "normal"
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_ODDS

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=KNIGHTODDSSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

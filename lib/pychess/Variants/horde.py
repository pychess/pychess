""" Horde Variant"""
from pychess.Utils.const import HORDECHESS, VARIANTS_OTHER_NONSTANDARD
from pychess.Utils.Board import Board

HORDESTART = "rnbqkbnr/pppppppp/8/1PP2PP1/PPPPPPPP/PPPPPPPP/PPPPPPPP/PPPPPPPP w kq - 0 1"


class HordeBoard(Board):
    """:Description: Lichess horde: https://lichess.org/variant/horde
    """
    variant = HORDECHESS
    __desc__ = _("Black have to capture all white pieces to win.\n" +
                 "White wants to checkmate as usual.\n" +
                 "White pawns on the first rank may move two squares,\n" +
                 "similar to pawns on the second rank.")
    name = _("Horde")
    cecp_name = "horde"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD

    FILES = 8
    # We need additional holdings for captured white horde...
    HOLDING_FILES = ((FILES + 3, FILES + 2, FILES + 1), (-6, -5, -4, -3, -2))

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=HORDESTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

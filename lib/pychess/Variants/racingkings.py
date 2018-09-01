""" The Racing Kings Variation"""

from pychess.Utils.const import RACINGKINGSCHESS, VARIANTS_OTHER_NONSTANDARD, \
    A8, B8, C8, D8, E8, F8, G8, H8
from pychess.Utils.Board import Board

RACINGKINGSSTART = "8/8/8/8/8/8/krbnNBRK/qrbnNBRQ w - - 0 1"

RANK8 = (A8, B8, C8, D8, E8, F8, G8, H8)


class RacingKingsBoard(Board):
    """ :Description: The Racing Kings variation is where the object of the game
        is to bring your king to the eight row.
    """
    variant = RACINGKINGSCHESS
    __desc__ = _(
        "In this game, check is entirely forbidden: not only is it forbidden\n" +
        "to move ones king into check, but it is also forbidden to check the opponents king.\n" +
        "The purpose of the game is to be the first player that moves his king to the eight row.\n" +
        "When white moves their king to the eight row, and black moves directly after that also\n" +
        "their king to the last row, the game is a draw\n" +
        "(this rule is to compensate for the advantage of white that they may move first.)\n" +
        "Apart from the above, pieces move and capture precisely as in normal chess."
    )
    name = _("Racing Kings")
    cecp_name = "racingkings"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=RACINGKINGSSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)


def testKingInEightRow(board):
    """ Test for a winning position """
    return board.kings[board.color - 1] in RANK8


def test2KingInEightRow(board):
    """ Test for a winning position """
    return board.kings[board.color] in RANK8 and board.kings[board.color - 1] in RANK8

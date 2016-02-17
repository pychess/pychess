""" The King of the Hill Variation"""

from pychess.Utils.const import KINGOFTHEHILLCHESS, VARIANTS_OTHER_NONSTANDARD, \
    D4, D5, E4, E5
from pychess.Utils.Board import Board


class KingOfTheHillBoard(Board):
    """ :Description: The King of the hill variation is where the object of the game
        is to try and manoeuvre to the centre of the board. The gmae is won when one player
        manages to get there king to any of the 4 centre square ie d4, d5, e4, e5
    """
    variant = KINGOFTHEHILLCHESS
    __desc__ = _(
        "Bringing your king legally to the center (e4, d4, e5, d5) instantly wins the game!\n" +
        "Normal rules apply in other cases and checkmate also ends the game.")
    name = _("King of the hill")
    cecp_name = "kingofthehill"
    need_initial_board = False
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD


def testKingInCenter(board):
    """ Test for a winning position """
    return board.kings[board.color - 1] in (E4, E5, D4, D5)

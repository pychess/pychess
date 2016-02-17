""" Losers Variant"""

from pychess.Utils.const import LOSERSCHESS, VARIANTS_OTHER_NONSTANDARD
from pychess.Utils.Board import Board


class LosersBoard(Board):
    """:Description: The Losers variant is a game where the concept is to get rid of all your
        pieces before you opponent does. On a players turn if a piece can be taken it must be taken
        otherwise a normal chess move can be played
    """
    variant = LOSERSCHESS
    __desc__ = _("FICS losers: http://www.freechess.org/Help/HelpFiles/losers_chess.html")
    name = _("Losers")
    cecp_name = "losers"
    need_initial_board = False
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD


def testKingOnly(board):
    """ Checks to see if if a winning position has been acheived
    """
    return bin(board.friends[board.color]).count("1") == 1

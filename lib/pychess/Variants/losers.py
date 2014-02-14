# Losers Chess

from pychess.Utils.const import *
from pychess.Utils.Board import Board

class LosersBoard(Board):
    variant = LOSERSCHESS


class LosersChess:
    __desc__ = _("FICS losers: http://www.freechess.org/Help/HelpFiles/losers_chess.html")
    name = _("Losers")
    cecp_name = "losers"
    board = LosersBoard
    need_initial_board = False
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD


def testKingOnly(board):
    return bin(board.friends[board.color]).count("1") == 1

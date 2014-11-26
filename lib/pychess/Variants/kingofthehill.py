# Losers Chess

from pychess.Utils.const import *
from pychess.Utils.Board import Board

class KingOfTheHillBoard(Board):
    variant = KINGOFTHEHILLCHESS


class KingOfTheHillChess:
    __desc__ = _("Bringing your king legally to the center (e4, d4, e5, d5) instantly wins the game!\n" +
                 "Normal rules apply in other cases and checkmate also ends the game.")
    name = _("King of the hill")
    cecp_name = "king-of-the-hill"
    board = KingOfTheHillBoard
    need_initial_board = False
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD


def testKingInCenter(board):
    return board.kings[board.color-1] in (E4, E5, D4, D5)

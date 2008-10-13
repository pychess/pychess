# Losers Chess
# http://www.freechess.org/Help/HelpFiles/losers_chess.html

from pychess.Utils.const import *
from pychess.Utils.lutils.bitboard import bitLength
from pychess.Utils.Board import Board


class LosersBoard(Board):
    variant = LOSERSCHESS


class LosersChess:
    name = _("Losers")
    cecp_name = "losers"
    board = LosersBoard
    need_initial_board = False
    standard_rules = False
    variant_group = VARIANTS_OTHER


def testKingOnly(board):
    boards = board.boards[board.color]
    
    return bitLength(boards[PAWN]) + bitLength(boards[KNIGHT]) + \
           bitLength(boards[BISHOP]) + bitLength(boards[ROOK]) + \
           bitLength(boards[QUEEN]) == 0

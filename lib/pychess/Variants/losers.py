# Losers Chess
# http://www.freechess.org/Help/HelpFiles/losers_chess.html

import random

# used only for selftesting
#import __builtin__
#__builtin__.__dict__['_'] = lambda s: s

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


def testKingOnly(board):
    boards = board.boards[board.color]
    
    return bitLength(boards[PAWN]) + bitLength(boards[KNIGHT]) + \
           bitLength(boards[BISHOP]) + bitLength(boards[ROOK]) + \
           bitLength(boards[QUEEN]) == 0

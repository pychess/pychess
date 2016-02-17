from __future__ import absolute_import
from __future__ import print_function
import sys

from .attack import staticExchangeEvaluate
from .ldata import PIECE_VALUES, ASEAN_PIECE_VALUES, PAWN_VALUE, MATE_VALUE
from pychess.Utils.const import DROP, EMPTY, ASEAN_VARIANTS, PROMOTIONS, ATOMICCHESS
from pychess.Utils.eval import pos as position_values
from pychess.Variants.atomic import kingExplode


def getCaptureValue(board, move):
    if board.variant in ASEAN_VARIANTS:
        mpV = ASEAN_PIECE_VALUES[board.arBoard[move >> 6 & 63]]
        cpV = ASEAN_PIECE_VALUES[board.arBoard[move & 63]]
    else:
        mpV = PIECE_VALUES[board.arBoard[move >> 6 & 63]]
        cpV = PIECE_VALUES[board.arBoard[move & 63]]
    if mpV < cpV:
        return cpV - mpV
    else:
        temp = staticExchangeEvaluate(board, move)
        return temp < 0 and -sys.maxsize or temp


def sortCaptures(board, moves):
    def sort_captures_func(move):
        return getCaptureValue(board, move)
    moves.sort(key=sort_captures_func, reverse=True)
    return moves


def getMoveValue(board, table, depth, move):
    """ Sort criteria is as follows.
        1.  The move from the hash table
        2.  Captures as above.
        3.  Killers.
        4.  History.
        5.  Moves to the centre. """

    # As we only return directly from transposition table if hashf == hashfEXACT
    # There could be a non  hashfEXACT very promising move for us to test

    if table.isHashMove(depth, move):
        return sys.maxsize

    fcord = (move >> 6) & 63
    tcord = move & 63
    flag = move >> 12

    arBoard = board.arBoard
    fpiece = fcord if flag == DROP else arBoard[fcord]
    tpiece = arBoard[tcord]

    if tpiece != EMPTY:
        if board.variant == ATOMICCHESS:
            if kingExplode(board, move, board.color):
                return MATE_VALUE
        # We add some extra to ensure also bad captures will be searched early
        if board.variant in ASEAN_VARIANTS:
            return ASEAN_PIECE_VALUES[tpiece] - PIECE_VALUES[fpiece] + 1000
        else:
            return PIECE_VALUES[tpiece] - PIECE_VALUES[fpiece] + 1000

    if flag in PROMOTIONS:
        if board.variant in ASEAN_VARIANTS:
            return ASEAN_PIECE_VALUES[flag - 3] - PAWN_VALUE + 1000
        else:
            return PIECE_VALUES[flag - 3] - PAWN_VALUE + 1000

    if flag == DROP:
        return PIECE_VALUES[tpiece] + 1000

    killervalue = table.isKiller(depth, move)
    if killervalue:
        return 1000 + killervalue

    # King tropism - a move that brings us nearer to the enemy king, is probably
    # a good move
    # opking = board.kings[1-board.color]
    # score = distance[fpiece][fcord][opking] - distance[fpiece][tcord][opking]

    if fpiece not in position_values:
        # That is, fpiece == EMPTY
        print(fcord, tcord)
        print(board)

    if board.variant in ASEAN_VARIANTS:
        score = 0
    else:
        score = position_values[fpiece][board.color][tcord] - \
            position_values[fpiece][board.color][fcord]

    # History heuristic
    score += table.getButterfly(move)

    return score


def sortMoves(board, table, ply, hashmove, moves):
    def sort_moves_func(move):
        return getMoveValue(board, table, ply, hashmove, move)
    moves.sort(key=sort_moves_func, reverse=True)
    return moves

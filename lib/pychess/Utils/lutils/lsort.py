
from attack import getAttacks, staticExchangeEvaluate
from pychess.Utils.eval import pos as positionValues

from sys import maxint
from ldata import *

def getCaptureValue (board, move):
    mpV = PIECE_VALUES[board.arBoard[move>>6 & 63]]
    cpV = PIECE_VALUES[board.arBoard[move & 63]]
    if mpV < cpV:
        return cpV - mpV
    else:
        temp = staticExchangeEvaluate (board, move)
        return temp < 0 and -maxint or temp

def sortCaptures (board, moves):
    f = lambda move: getCaptureValue (board, move)
    moves.sort(key=f, reverse=True)
    return moves

def getMoveValue (board, table, depth, move):
    """ Sort criteria is as follows.
        1.  The move from the hash table
        2.  Captures as above.
        3.  Killers.
        4.  History.
        5.  Moves to the centre. """
    
    # As we only return directly from transposition table if hashf == hashfEXACT
    # There could be a non  hashfEXACT very promising move for us to test
    
    if table.isHashMove(depth, move):
        return maxint
    
    fcord = (move >> 6) & 63
    tcord = move & 63
    
    arBoard = board.arBoard
    fpiece = arBoard[fcord]
    tpiece = arBoard[tcord]
    
    if tpiece != EMPTY:
        # We add some extra to ensure also bad captures will be searched early
        return PIECE_VALUES[tpiece] - PIECE_VALUES[fpiece] + 1000
    
    flag = move >> 12
    
    if flag in PROMOTIONS:
        return PIECE_VALUES[flag-3] - PAWN_VALUE + 1000
    
    killervalue = table.isKiller(depth, move)
    if killervalue:
        return 1000 + killervalue
    
    # King tropism - a move that brings us nearer to the enemy king, is probably
    # a good move
    #opking = board.kings[1-board.color]
    #score = distance[fpiece][fcord][opking] - distance[fpiece][tcord][opking]
    
    if fpiece not in positionValues:
        # That is, fpiece == EMPTY
        print fcord, tcord
        print repr(board)
    score = positionValues[fpiece][board.color][tcord] - \
            positionValues[fpiece][board.color][fcord]
    
    # History heuristic
    score += table.getButterfly(move)
    
    return score

def sortMoves (board, table, ply, hashmove, moves):
    f = lambda move: getMoveValue (board, table, ply, hashmove, move)
    moves.sort(key=f, reverse=True)
    return moves

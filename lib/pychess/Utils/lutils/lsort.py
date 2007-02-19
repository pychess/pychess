
from attack import getAttacks, addXrayPiece, swapOff, xray

def staticExchangeEvaluate (board, move):
    """ The GnuChess Static Exchange Evaluator (or SEE for short).
    First determine the target square.  Create a bitboard of all squares
    attacking the target square for both sides.  Using these 2 bitboards,
    we take turn making captures from smallest piece to largest piece.
    When a sliding piece makes a capture, we check behind it to see if
    another attacker piece has been exposed.  If so, add this to the bitboard
    as well.  When performing the "captures", we stop if one side is ahead
    and doesn't need to capture, a form of pseudo-minimaxing. """
    
    swaplist = []
    
    flag = move >> 12
    fcord = (move >> 6) & 63
    tcord = move & 63
    
    color = board.friends[BLACK] & bitPosArray[fcord] and BLACK or WHITE
    opcolor = 1-color
    
    pieces = board.arBoard
    
    ours = getAttacks (board, tcord, color)
    ours = clearBit (ours, fcord)
    theirs = getAttacks (board, tcord, opcolor)
    
    if xray[pieces[fcord]]:
        ours, theirs = addXrayPiece (board, tcord, fcord, color, ours, theirs)
    
    if flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                BISHOP_PROMOTION, KNIGHT_PROMOTION):
        swaplist.append(PIECE_VALUES[flag-3] - PAWN_VALUE)
        lastval = -PIECE_VALUES[flag-3]
    else:
        if flag == ENPASSANT:
            swaplist.append(PAWN_VALUE)
        else: swaplist.append(PIECE_VALUES[pieces[tcord]])
        lastval = -PIECE_VALUES[pieces[fcord]]
    
    return swapOff (board, tcord, swaplist, lastval, ours, theirs)

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

def getMoveValue (board, table, ply, move):
    """ Sort criteria is as follows.
        1.  The move from the hash table
        2.  Captures as above.
        3.  Killers.
        4.  History.
        5.  Moves to the centre. """
    
    color = board.color
    opcolor = 1-color
    enemyPawns = board.boards[opcolor][PAWN]
    
    score = -maxint
    
    flag = move >> 12
    fcord = (move >> 6) & 63
    tcord = move & 63
    
    # As we only return directly from transposition table if hashf == hashfEXACT
    # There will be a very promising move we could test
    if table.isHashMove(ply, move):
        return maxint
    
    arBoard = board.arBoard
    fpiece = arBoard[fcord]
    tpiece = arBoard[tcord]
    
    if tpiece != EMPTY:
        # We add some extra to ensure also bad captures will be searched early
        return PIECE_VALUES[tpiece] - PIECE_VALUES[fpiece] + 1000
    if flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                BISHOP_PROMOTION, KNIGHT_PROMOTION):
        return PIECE_VALUES[flag-3] - PAWN_VALUE + 1000
    
    if table.isKiller(ply, move):
        return 1000
    
    # King tropism - a move that brings us nearer to the enemy king, is probably
    # a good move
    opking = board.kings[opcolor]
    return 10-distance[tcord][opking]

def sortMoves (board, table, ply, moves):
    f = lambda move: getMoveValue (board, table, ply, move)
    moves.sort(key=f, reverse=True)
    return moves

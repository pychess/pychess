
from attack import getAttacks

MAXPLYDEPTH = 65 # This is the gnuchess value, we might have to set it lower
xray = (False, True, False, True, True, True, False)

def staticExchangeEvaluate (board, move):
    """ The GnuChess Static Exchange Evaluator (or SEE for short).
    First determine the target square.  Create a bitboard of all squares
    attacking the target square for both sides.  Using these 2 bitboards,
    we take turn making captures from smallest piece to largest piece.
    When a sliding piece makes a capture, we check behind it to see if
    another attacker piece has been exposed.  If so, add this to the bitboard
    as well.  When performing the "captures", we stop if one side is ahead
    and doesn't need to capture, a form of pseudo-minimaxing. """
    
    swaplist = [0]*MAXPLYDEPTH
    
    flag = move >> 12
    fcord = (move >> 6) & 63
    tcord = move & 63
    
    color = board.friends[BLACK] & bitPosArray[fcord] and BLACK or WHITE
    opcolor = 1-color
    
    pieces = board.arBoard
    
    ours = getAttacks (board, tcord, color)
    ours = clearBit (ours, fcord)
    theirs = getAttacks (board, tcord, opcolor)
    
    if xray[pieces[f]]:
        ours, theirs = addXrayPiece (board, tcord, fcord, color, ours, theirs)
    
    d = board.boards[color]
    e = board.boards[opcolor]
    if flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                BISHOP_PROMOTION, KNIGHT_PROMOTION):
        swaplist[0] = PIECE_VALUES[flag-3] - PAWN_VALUE
        lastval = -PIECE_VALUES[flag-3]
    else:
        swaplist[0] = flag == ENPASSANT and PAWN_VALUE or \
                                            PIECE_VALUES[pieces[tcord]]
        lastval = -PIECE_VALUES[pieces[fcord]]
    
    n = 1
    while theirs:
        for piece in range(PAWN, KING+1):
            r = theirs & e[piece]
            if r:
                cord = firstBit(r)
                theirs = clearBit(theirs, cord)
                if xray[piece]:
                    ours, theirs = addXrayPiece (board, tcord, fcord,
                                                 color, ours, theirs)
                swaplist[n] = swaplist[n-1] + lastval
                n += 1
                lastval = PIECE_VALUES[piece]
                break
        
        if not ours: break
        for piece in range(PAWN, KING+1):
            r = ours & d[piece]
            if r:
                cord = firstBit(r)
                ours = clearBit(ours, cord)
                if xray[piece]:
                    ours, theirs = addXrayPiece (board, tcord, fcord,
                                                 color, ours, theirs)
                swaplist[n] = swaplist[n-1] + lastval
                n += 1
                lastval = PIECE_VALUES[piece]
                break
                
    ############################################################################
    #  At this stage, we have the swap scores in a list.  We just need to      #
    #  mini-max the scores from the bottom up to the top of the list.          #
    ############################################################################
    n -= 1
    while n:
        if n & 1:
            if swaplist[n] <= swaplist[n-1]:
                swaplist[n-1] = swaplist[n] 
        else:
            if swaplist[n] >= swaplist[n-1]:
                swaplist[n-1] = swaplist[n] 
        n -= 1

    return swaplist[0]

def addXrayPiece (board, tcord, fcord, color, ours, theirs):
    """ The purpose of this routine is to find a piece which attack through
    another piece (e.g. two rooks, Q+B, B+P, etc.) Color is the side attacking
    the square where the swapping is to be done. """
    
    dir = directions[tcord][fcord]
    a = rays[fcord][dir] & board.blocker
    if not a: return ours, theirs
    
    ncord = tcord < fcord and firstBit(a) or lastBit(a)
    piece = board.arBoard[ncord]
    if piece == QUEEN or (piece == ROOK and dir > 3) or \
                         (piece == BISHOP and dir < 4):
        bit = bitPosArray[ncord]
        if bit & board.friends[color]:
            ours |= bit
        else: theirs |= bit
    
    return ours, theirs

from sys import maxint
from ldata import *

def getCaptureValue (move):
    global gboard
    arBoard = gboard.arBoard
    mpV = PIECE_VALUES[arBoard[move>>6 & 63]]
    cpV = PIECE_VALUES[arBoard[move & 63]]
    if mpV < cpV:
        return cpV - mpV
    else:
        temp = staticExchangeEvaluate (gboard, move)
        return temp < 0 and -maxint or temp

def sortCaptures (board, moves):
    global gboard
    gboard = board
    moves.sort(key=getCaptureValue, reverse=True)
    return moves

from sys import maxint

def getMoveValue (move):
    """ Sort criteria is as follows.
        1.  The move from the hash table
        2.  Captures as above.
        3.  Killers.
        4.  History.
        5.  Moves to the centre. """
    
    global gboard, gtable, gply
    
    color = gboard.color
    opcolor = 1-color
    enemyPawns = gboard.boards[opcolor][PAWN]
    
    score = -maxint
    
    flag = move >> 12
    fcord = (move >> 6) & 63
    tcord = move & 63
    
    # As we only return directly from transposition table if hashf == hashfEXACT
    # There will be a very promising move we could test
    if gtable.isHashMove(gply, move):
        return maxint
    
    arBoard = gboard.arBoard
    fpiece = arBoard[fcord]
    tpiece = arBoard[tcord]
    
    score = 0
    if tpiece != EMPTY:
        # We add some extra to ensure also bad captures will be searched early
        score += PIECE_VALUES[tpiece] - PIECE_VALUES[fpiece] + 1000
    if flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                BISHOP_PROMOTION, KNIGHT_PROMOTION):
        score += PIECE_VALUES[flag-3] - PAWN_VALUE + 1000
    return score
    
    if gtable.isKiller(gboard.color, len(gboard.history), move):
        return 1000
    
    # King tropism - a move makeing us nearer to the enemy king, is probably a
    # good move
    opking = gboard.kings[opcolor]
    return 10-distance[tcord][opking]

def sortMoves (board, table, ply, moves):
    global gboard, gtable, gply
    gboard = board
    gtable = table
    gply = ply
    moves.sort(key=getMoveValue, reverse=True)
    return moves

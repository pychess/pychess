
from bitboard import *
from attack import isAttacked
from const import *

shift00 = [
    56, 56, 56, 56, 56, 56, 56, 56,
    48, 48, 48, 48, 48, 48, 48, 48,
    40, 40, 40, 40, 40, 40, 40, 40,
    32, 32, 32, 32, 32, 32, 32, 32,
    24, 24, 24, 24, 24, 24, 24, 24,
    16, 16, 16, 16, 16, 16, 16, 16,
     8,  8,  8,  8,  8,  8,  8,  8,
     0,  0,  0,  0,  0,  0,  0,  0
]

shift90 = [
    0, 8, 16, 24, 32, 40, 48, 56,
    0, 8, 16, 24, 32, 40, 48, 56,
    0, 8, 16, 24, 32, 40, 48, 56,
    0, 8, 16, 24, 32, 40, 48, 56,
    0, 8, 16, 24, 32, 40, 48, 56,
    0, 8, 16, 24, 32, 40, 48, 56,
    0, 8, 16, 24, 32, 40, 48, 56,
    0, 8, 16, 24, 32, 40, 48, 56
]

shift45 = [
    28, 36, 43, 49, 54, 58, 61, 63,
    21, 28, 36, 43, 49, 54, 58, 61,
    15, 21, 28, 36, 43, 49, 54, 58,
    10, 15, 21, 28, 36, 43, 49, 54,
     6, 10, 15, 21, 28, 36, 43, 49,
     3,  6, 10, 15, 21, 28, 36, 43,
     1,  3,  6, 10, 15, 21, 28, 36,
     0,  1,  3,  6, 10, 15, 21, 28
]
     
mask45 = [
    0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 0x07, 0x03, 0x01,
    0x7F, 0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 0x07, 0x03, 
    0x3F, 0x7F, 0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 0x07, 
    0x1F, 0x3F, 0x7F, 0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 
    0x0F, 0x1F, 0x3F, 0x7F, 0xFF, 0x7F, 0x3F, 0x1F, 
    0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF, 0x7F, 0x3F, 
    0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF, 0x7F, 
    0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF
]

shift315 = [
    63, 61, 58, 54, 49, 43, 36, 28,
    61, 58, 54, 49, 43, 36, 28, 21,
    58, 54, 49, 43, 36, 28, 21, 15,
    54, 49, 43, 36, 28, 21, 15, 10,
    49, 43, 36, 28, 21, 15, 10,  6,
    43, 36, 28, 21, 15, 10,  6,  3,
    36, 28, 21, 15, 10,  6,  3,  1,
    28, 21, 15, 10,  6,  3,  1,  0
]

mask315 = [
    0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF,
    0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF, 0x7F,
    0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF, 0x7F, 0x3F,
    0x0F, 0x1F, 0x3F, 0x7F, 0xFF, 0x7F, 0x3F, 0x1F,
    0x1F, 0x3F, 0x7F, 0xFF, 0x7F, 0x3F, 0x1F, 0x0F,
    0x3F, 0x7F, 0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 0x07,
    0x7F, 0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 0x07, 0x03,
    0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 0x07, 0x03, 0x01
]

#   3 bits:  Descriping the captured piece, if any - set when move applied     #

################################################################################
#   The format of a move is as follows - from left:                            #
#   4 bits:  Descriping the type of the move                                   #
#   6 bits:  cord to move from                                                 #
#   6 bits:  cord to move to                                                   #
################################################################################

#NULLMOVE = 0

NORMAL_MOVE, QUEEN_CASTLE, KING_CASTLE, CAPTURE, ENPASSANT, \
KNIGHT_PROMOTION, BISHOP_PROMOTION, ROOK_PROMOTION, QUEEN_PROMOTION = range(9)

S_NORMAL_MOVE, S_QUEEN_CASTLE, S_KING_CASTLE, S_CAPTURE, S_ENPASSANT, \
S_KNIGHT_PROMOTION, S_BISHOP_PROMOTION, S_ROOK_PROMOTION, S_QUEEN_PROMOTION = \
                                                     [v << 12 for v in range(9)]

# To unmake moves, we need to know which piece has been captured

shiftedFromCords = []
for i in range(64):
    shiftedFromCords.append(i << 6)

def newMove (fromcord, tocord, type = S_NORMAL_MOVE):
    return type + shiftedFromCords[fromcord] + tocord

def newPromotes (fromcord, tocord):
    for p in S_KNIGHT_PROMOTION, S_BISHOP_PROMOTION, \
             S_ROOK_PROMOTION, S_QUEEN_PROMOTION:
        yield newMove(fromcord, tocord, p)

################################################################################
#   bitsToMoves                                                                #
################################################################################

def bitsToMoves (fromcord, tobits):
    while (tobits):
        c = firstBit (tobits)
        tobits = clearBit (tobits, c)
        yield newMove(fromcord, c)

################################################################################
#   Create bit attack maps                                                     #
################################################################################

def bishopAttack (board, cord):
    return bishop45Attack[cord] \
                    [ (board.blocker45 >> shift45[cord]) & mask45[cord] ] | \
           bishop315Attack[cord] \
                    [ (board.blocker315 >> shift315[cord]) & mask315[cord] ]

def rookAttack (board, cord):
    return rook00Attack[cord][(board.blocker >> shift00[cord]) & 0xFF] | \
           rook90Attack[cord][(board.blocker90 >> shift90[cord]) & 0xFF]

def queenAttack (board, cord):
    return bishopAttack(board,cord) | rookAttack(board,cord)

################################################################################
#   Generate all moves                                                         #
################################################################################

def genAllMoves (board):
    
    blocker = board.blocker
    notblocker = ~blocker
    enpassant = board.enpassant
    
    friends = board.friends[board.color]
    notfriends = ~friends
    enemies = board.friends[1- board.color]
    
    pawns = board.boards[board.color][PAWN]
    knights = board.boards[board.color][KNIGHT]
    bishops = board.boards[board.color][BISHOP]
    rooks = board.boards[board.color][ROOK]
    queens = board.boards[board.color][QUEEN]
    kings = board.boards[board.color][KING]
    
    # Knights
    knightMoves = moveArray[KNIGHT]
    while knights:
        cord = firstBit( knights )
        knights = clearBit (knights, cord)
        for move in bitsToMoves (cord, knightMoves[cord] & notfriends):
            print 1; yield move
    
    # King
    kingMoves = moveArray[KING]
    cord = firstBit( kings )
    for move in bitsToMoves (cord, kingMoves[cord] & notfriends):
        print 2; yield move
    
    # Rooks
    while rooks:
        cord = firstBit (rooks)
        rooks = clearBit (rooks, cord)
        attackBoard = rookAttack(board, cord)
        for move in bitsToMoves (cord, attackBoard & notfriends):
            print 3; yield move
    
    # Bishops
    while bishops:
        cord = firstBit (bishops)
        bishops = clearBit (bishops, cord)
        attackBoard = bishopAttack(board, cord)
        for move in bitsToMoves (cord, attackBoard & notfriends):
            print 4; yield move
    
    # Queens
    while queens:
        cord = firstBit (queens)
        queens = clearBit (queens, cord)
        attackBoard = queenAttack(board, cord)
        for move in bitsToMoves (cord, attackBoard & notfriends):
            print 5; yield move
    
    # White pawns
    pawnEnemies = enemies | (enpassant != None and bitPosArray[enpassant] or 0)
    if board.color == WHITE:
        
        # One step
        
        movedpawns = (pawns >> 8) & notblocker # Move all pawns one step forward
        for cord in iterBits(movedpawns):
            if cord >= 56:
                for move in newPromotes (cord-8, cord):
                    print 6; yield move
            else:
                print 7; yield newMove (cord-8, cord)
        
        # Two steps
        
        seccondrow = pawns & rankBits[1] # Get seccond row pawns
        movedpawns = (seccondrow >> 8) & notblocker # Move two steps forward, while
        movedpawns = (movedpawns >> 8) & notblocker # ensuring middle cord is clear
        for cord in iterBits(movedpawns):
            print 8; yield newMove (cord-16, cord)
        
        # Capture left
        
        capLeftPawns = pawns & ~fileBits[0]
        capLeftPawns = (capLeftPawns >> 7) & pawnEnemies
        for cord in iterBits(capLeftPawns):
            if cord >= 56:
                for move in newPromotes (cord-7, cord):
                    print 9; yield move
            elif cord == enpassant:
                print 10; yield newMove (cord-7, cord, S_ENPASSANT)
            else:
                print 11; yield newMove (cord-7, cord)
        
        # Capture right
        
        capRightPawns = pawns & ~fileBits[7]
        capRightPawns = (capRightPawns >> 9) & pawnEnemies
        for cord in iterBits(capRightPawns):
            if cord >= 56:
                for move in newPromotes (cord-9, cord):
                    print 12; yield move
            elif cord == enpassant:
                print 13; yield newMove (cord-9, cord, S_ENPASSANT)
            else:
                print 14; yield newMove (cord-9, cord)
    
    # Black pawns
    else:
        
        # One step
        
        movedpawns = (pawns << 8) & notblocker # Move all pawns one step forward
        for cord in iterBits(movedpawns):
            if cord <= 7:
                for move in newPromotes (cord+8, cord):
                    print 15; yield move
            else:
                print 16; yield newMove (cord+8, cord)
        
        # Two steps
        
        seccondrow = pawns & rankBits[6] # Get seventh row pawns
        movedpawns = (seccondrow << 8) & notblocker # Move two steps forward, while
        movedpawns = (movedpawns << 8) & notblocker # ensuring middle cord is clear
        for cord in iterBits(movedpawns):
            print 17; yield newMove (cord+16, cord)
        
        # Capture left
        
        capLeftPawns = pawns & ~fileBits[7]
        capLeftPawns = (capLeftPawns << 7) & pawnEnemies
        for cord in iterBits(capLeftPawns):
            if cord <= 7:
                for move in newPromotes (cord+7, cord):
                    print 18; yield move
            elif cord == enpassant:
                print 19; yield newMove (cord+7, cord, S_ENPASSANT)
            else:
               print 20; yield newMove (cord+7, cord)
        
        # Capture right
        
        capRightPawns = pawns & ~fileBits[0]
        capRightPawns = (capRightPawns << 9) & pawnEnemies
        for cord in iterBits(capRightPawns):
            if cord <= 7:
                for move in newPromotes (cord+9, cord):
                    print 21; yield move
            elif cord == enpassant:
                print 22; yield newMove (cord+9, cord, S_ENPASSANT)
            else:
                print 23; yield newMove (cord+9, cord)
    
    # Castling
    
    if board.color == WHITE:
        if board.castling & W_OO and not fromToRay[E1][G1] & blocker and \
            not isAttacked (board, E1, BLACK) and \
            not isAttacked (board, F1, BLACK) and \
            not isAttacked (board, G1, BLACK):
                print 24; yield newMove (E1, G1, S_KING_CASTLE)
                
        if board.castling & W_OOO and not fromToRay[E1][B1] & blocker and \
            not isAttacked (board, E1, BLACK) and \
            not isAttacked (board, D1, BLACK) and \
            not isAttacked (board, C1, BLACK):
                print 25; yield newMove (E1, B1, S_QUEEN_CASTLE)
    
    else:
        if board.castling & B_OO and not fromToRay[E8][G8] & blocker and \
            not isAttacked (board, E8, WHITE) and \
            not isAttacked (board, F8, WHITE) and \
            not isAttacked (board, G8, WHITE):
                print 26; yield newMove (E8, G8, S_KING_CASTLE)
                
        if board.castling & B_OOO and not fromToRay[E8][B8] & blocker and \
            not isAttacked (board, E8, WHITE) and \
            not isAttacked (board, D8, WHITE) and \
            not isAttacked (board, C8, WHITE):
                print 27; yield newMove (E8, B8, S_QUEEN_CASTLE)

def genCheckEvasions (board):
    
    color = board.color
    opcolor = 1-color
    
    kingsq = board.king[color]
    kings = board.boards[color][KING]
    pawns = board.boards[color][PAWN]
    checkers = getAttacks (board, kingsq, color)
    
    arBoard = board.arBoard
    
    if bitLength(checkers) == 1:
        # Captures of checking pieces (except by king, which we will test later)
        chkcord = firstBit (checkers)
        b = getAttacks (chksq, color) & ~kings
        while b:
            cord = firstBit (b)
            b = clearBit (b, cord)
            if not pinnedOnKing (board, cord, color):
                if arBoard[cord] == PAWN and \
                        (chkcord <= H1 or chkcord >= A8):
                    for move in newPromotes (cord, chkcord):
                        yield move
                else:
                    yield newMove (cord, chkcord)
        
        # Maybe enpassant can help
        if board.enpassant:
            ep = board.enpassant
            if ep + (color == WHITE and -8 or 8) == chkcord:
                bits = moveArray[color == WHITE and PAWN or BPAWN][ep] & pawns
                for cord in iterBits (bits):
                    if not pinnedOnKing (board, cord, color):
                        yield newMove (cord, ep, S_ENPASSANT)
        
        # Lets block/capture the checking piece
        if slider[arBoard[chkcord]]:
            bits = clearBit(fromToRay[kingcord][chkcord], chkcord)
            for cord in iterBits (bits):
                b = getAttacks (cord, color)
                b &= ~(kings | pawns)
                
                if color == WHITE and cord > H2:
                    if bitPosArray[cord-8] & pawns:
                        b |= bitPosArray[cord-8]
                    if cord >> 3 == 3 and arBoard[cord-8] == EMPTY and \
                            bitPosArray[cord-16] and pawns:
                        b |= bitPosArray[cord-16]
                
                elif color == BLACK and cord < H7:
                    if bitPosArray[cord88] & pawns:
                        b |= bitPosArray[cord88]
                    if cord >> 3 == 4 and arBoard[cord88] == EMPTY and \
                            bitPosArray[cord+16] and pawns:
                        b |= bitPosArray[cord+16]
                
                for cord1 in iterBits (b):
                    if pinnedOnKing (board, cord1, color):
                        continue
                    if arBoard[cord1] == PAWN and (cord > H7 or cord < A2):
                        for move in newPromotes (cord1, cord):
                            yield move
                    else:
                        yield newMove (cord1, cord)
    
    # If more than one checkers, move king to get out of check
    if checkers:
        escapes = moveArray[KING][kingcord] & ~board.friends[color]
    else: escaped = 0
    
    for chkcord in iterBits (chekers):
        dir = directions[chkcord][kingcord]
        if slider[arBoard[chkcord]]:
            escapes &= ray[chkcord][dir]
            
    for cord in iterBits (escapes):
        if not isAttacked (board, cord, color):
            yield newMove (kingcord, cord)

def willCheck (board, move):
    """ Returns true if move will leave moving player in check """
    board.applyMove (move)
    checked = isCheck (board, 1-board.color)
    board.popMove()
    return checked

def isCheck (board, color):
    kingcord = board.kings[color]
    return isAttacked (board, kingcord, 1-color)

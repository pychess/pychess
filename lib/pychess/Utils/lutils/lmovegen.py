
from bitboard import *
from attack import *
from pychess.Utils.const import *
from lmove import newMove


def newPromotes (fromcord, tocord):
    for p in PROMOTIONS:
        yield newMove(fromcord, tocord, p)

################################################################################
#   bitsToMoves                                                                #
################################################################################

def bitsToMoves (fromcord, tobits):
    for c in iterBits(tobits):
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

################################################################################
#   Generate all moves                                                         #
################################################################################

def genCastles (board):
    def generateOne (color, rooknum, king_after, rook_after):
        if rooknum == 0:
            castle = QUEEN_CASTLE
        else:
            castle = KING_CASTLE
        king = board.ini_kings[color]
        rook = board.ini_rooks[color][rooknum]
        blocker = clearBit(clearBit(board.blocker, king), rook)
        stepover = fromToRay[king][king_after] | fromToRay[rook][rook_after]
        if not stepover & blocker:
            for cord in xrange(min(king,king_after), max(king,king_after)+1):
                if isAttacked (board, cord, 1-color):
                    return
            return newMove (king, king_after, castle)
    
    if board.color == WHITE:
        if board.castling & W_OO:
            move = generateOne (WHITE, 1, G1, F1) 
            if move: yield move
        
        if board.castling & W_OOO:
            move = generateOne (WHITE, 0, C1, D1) 
            if move: yield move
    else:
        if board.castling & B_OO:
            move = generateOne (BLACK, 1, G8, F8) 
            if move: yield move
        
        if board.castling & B_OOO:
            move = generateOne (BLACK, 0, C8, D8) 
            if move: yield move

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
    for cord in iterBits(knights):
        for move in bitsToMoves (cord, knightMoves[cord] & notfriends):
            yield move
    
    # King
    kingMoves = moveArray[KING]
    cord = firstBit( kings )
    for move in bitsToMoves (cord, kingMoves[cord] & notfriends):
        yield move
    
    # Rooks and Queens
    for cord in iterBits(rooks | queens):
        attackBoard = attack00[cord][ray00[cord] & blocker] | \
                      attack90[cord][ray90[cord] & blocker]
        for move in bitsToMoves (cord, attackBoard & notfriends):
            yield move
    
    # Bishops and Queens
    for cord in iterBits(bishops | queens):
        attackBoard = attack45 [cord][ray45 [cord] & blocker] | \
                      attack135[cord][ray135[cord] & blocker]
        for move in bitsToMoves (cord, attackBoard & notfriends):
            yield move
    
    # White pawns
    pawnEnemies = enemies | (enpassant != None and bitPosArray[enpassant] or 0)
    if board.color == WHITE:
        
        # One step
        
        movedpawns = (pawns >> 8) & notblocker # Move all pawns one step forward
        for cord in iterBits(movedpawns):
            if cord >= 56:
                for move in newPromotes (cord-8, cord):
                    yield move
            else:
                yield newMove (cord-8, cord)
        
        # Two steps
        
        seccondrow = pawns & rankBits[1] # Get seccond row pawns
        movedpawns = (seccondrow >> 8) & notblocker # Move two steps forward, while
        movedpawns = (movedpawns >> 8) & notblocker # ensuring middle cord is clear
        for cord in iterBits(movedpawns):
            yield newMove (cord-16, cord)
        
        # Capture left
        
        capLeftPawns = pawns & ~fileBits[0]
        capLeftPawns = (capLeftPawns >> 7) & pawnEnemies
        for cord in iterBits(capLeftPawns):
            if cord >= 56:
                for move in newPromotes (cord-7, cord):
                    yield move
            elif cord == enpassant:
                yield newMove (cord-7, cord, ENPASSANT)
            else:
                yield newMove (cord-7, cord)
        
        # Capture right
        
        capRightPawns = pawns & ~fileBits[7]
        capRightPawns = (capRightPawns >> 9) & pawnEnemies
        for cord in iterBits(capRightPawns):
            if cord >= 56:
                for move in newPromotes (cord-9, cord):
                    yield move
            elif cord == enpassant:
                yield newMove (cord-9, cord, ENPASSANT)
            else:
                yield newMove (cord-9, cord)
    
    # Black pawns
    else:
        
        # One step
        
        movedpawns = (pawns << 8) & notblocker
        for cord in iterBits(movedpawns):
            if cord <= 7:
                for move in newPromotes (cord+8, cord):
                    yield move
            else:
                yield newMove (cord+8, cord)
        
        # Two steps
        
        seccondrow = pawns & rankBits[6] # Get seventh row pawns
        # Move two steps forward, while ensuring middle cord is clear
        movedpawns = seccondrow << 8 & notblocker
        movedpawns = movedpawns << 8 & notblocker
        for cord in iterBits(movedpawns):
            yield newMove (cord+16, cord)
        
        # Capture left
        
        capLeftPawns = pawns & ~fileBits[7]
        capLeftPawns = capLeftPawns << 7 & pawnEnemies
        for cord in iterBits(capLeftPawns):
            if cord <= 7:
                for move in newPromotes (cord+7, cord):
                    yield move
            elif cord == enpassant:
                yield newMove (cord+7, cord, ENPASSANT)
            else:
               yield newMove (cord+7, cord)
        
        # Capture right
        
        capRightPawns = pawns & ~fileBits[0]
        capRightPawns = capRightPawns << 9 & pawnEnemies
        for cord in iterBits(capRightPawns):
            if cord <= 7:
                for move in newPromotes (cord+9, cord):
                    yield move
            elif cord == enpassant:
                yield newMove (cord+9, cord, ENPASSANT)
            else:
                yield newMove (cord+9, cord)
    
    # Castling
    
    for m in genCastles(board):
        yield m

################################################################################
#   Generate capturing moves                                                   #
################################################################################

def genCaptures (board):
    
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
    for cord in iterBits(knights):
        for move in bitsToMoves (cord, knightMoves[cord] & enemies):
            yield move
    
    # King
    kingMoves = moveArray[KING]
    cord = firstBit( kings )
    for move in bitsToMoves (cord, kingMoves[cord] & enemies):
        yield move
    
    # Rooks and Queens
    for cord in iterBits(rooks|queens):
        attackBoard = attack00[cord][ray00[cord] & blocker] | \
                      attack90[cord][ray90[cord] & blocker]
        for move in bitsToMoves (cord, attackBoard & enemies):
            yield move
    
    # Bishops and Queens
    for cord in iterBits(bishops|queens):
        attackBoard = attack45 [cord][ray45 [cord] & blocker] | \
                      attack135[cord][ray135[cord] & blocker]
        for move in bitsToMoves (cord, attackBoard & enemies):
            yield move
    
    # White pawns
    pawnEnemies = enemies | (enpassant != None and bitPosArray[enpassant] or 0)
    
    if board.color == WHITE:
        
        # Promotes
        
        movedpawns = (pawns >> 8) & notblocker & rankBits[7]
        #for cord in iterBits(movedpawns):
        #    for move in newPromotes (cord-8, cord):
        #        yield move
        
        # Capture left
        
        capLeftPawns = pawns & ~fileBits[0]
        capLeftPawns = (capLeftPawns >> 7) & pawnEnemies
        for cord in iterBits(capLeftPawns):
            if cord >= 56:
                for move in newPromotes (cord-7, cord):
                    yield move
            elif cord == enpassant:
                yield newMove (cord-7, cord, ENPASSANT)
            else:
                yield newMove (cord-7, cord)
        
        # Capture right
        
        capRightPawns = pawns & ~fileBits[7]
        capRightPawns = (capRightPawns >> 9) & pawnEnemies
        for cord in iterBits(capRightPawns):
            if cord >= 56:
                for move in newPromotes (cord-9, cord):
                    yield move
            elif cord == enpassant:
                yield newMove (cord-9, cord, ENPASSANT)
            else:
                yield newMove (cord-9, cord)
    
    # Black pawns
    else:
        
        # One step
        
        movedpawns = pawns << 8 & notblocker & rankBits[0]
        #for cord in iterBits(movedpawns):
        #    for move in newPromotes (cord+8, cord):
        #        yield move
        
        # Capture left
        
        capLeftPawns = pawns & ~fileBits[7]
        capLeftPawns = capLeftPawns << 7 & pawnEnemies
        for cord in iterBits(capLeftPawns):
            if cord <= 7:
                for move in newPromotes (cord+7, cord):
                    yield move
            elif cord == enpassant:
                yield newMove (cord+7, cord, ENPASSANT)
            else:
                yield newMove (cord+7, cord)
        
        # Capture right
        
        capRightPawns = pawns & ~fileBits[0]
        capRightPawns = capRightPawns << 9 & pawnEnemies
        for cord in iterBits(capRightPawns):
            if cord <= 7:
                for move in newPromotes (cord+9, cord):
                    yield move
            elif cord == enpassant:
                yield newMove (cord+9, cord, ENPASSANT)
            else:
                yield newMove (cord+9, cord)

def genNonCaptures (board):
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
    for cord in iterBits(knights):
        for move in bitsToMoves (cord, knightMoves[cord] & notblocker):
            yield move
    
    # King
    kingMoves = moveArray[KING]
    cord = firstBit( kings )
    for move in bitsToMoves (cord, kingMoves[cord] & notblocker):
        yield move
    
    # Rooks and Queens
    for cord in iterBits(rooks):
        attackBoard = attack00[cord][ray00[cord] & blocker] | \
                      attack90[cord][ray90[cord] & blocker]
        for move in bitsToMoves (cord, attackBoard & notblocker):
            yield move
    
    # Bishops and Queens
    for cord in iterBits(bishops):
        attackBoard = attack45 [cord][ray45 [cord] & blocker] | \
                      attack135[cord][ray135[cord] & blocker]
        for move in bitsToMoves (cord, attackBoard & notblocker):
            yield move
    
    # White pawns
    if board.color == WHITE:
        
        # One step
        
        movedpawns = (pawns >> 8) & ~rankBits[7]
        for cord in iterBits(movedpawns):
            yield newMove (cord-8, cord)
        
        # Two steps
        
        seccondrow = pawns & rankBits[1] # Get seccond row pawns
        movedpawns = (seccondrow >> 8) & notblocker # Move two steps forward, while
        movedpawns = (movedpawns >> 8) & notblocker # ensuring middle cord is clear
        for cord in iterBits(movedpawns):
            yield newMove (cord-16, cord)
    
    # Black pawns
    else:
        
        # One step
        
        movedpawns = pawns << 8 & notblocker & ~rankBits[0]
        for cord in iterBits(movedpawns):
            yield newMove (cord+8, cord)
        
        # Two steps
        
        seccondrow = pawns & rankBits[6] # Get seventh row pawns
        # Move two steps forward, while ensuring middle cord is clear
        movedpawns = seccondrow << 8 & notblocker
        movedpawns = movedpawns << 8 & notblocker
        for cord in iterBits(movedpawns):
            yield newMove (cord+16, cord)
    
    # Castling
    
    for move in genCastles(board):
        yield move

################################################################################
#   Generate escapes from check                                                #
################################################################################

def genCheckEvasions (board):
    
    color = board.color
    opcolor = 1-color
    
    kcord = board.kings[color]
    kings = board.boards[color][KING]
    pawns = board.boards[color][PAWN]
    checkers = getAttacks (board, kcord, opcolor)
    
    arBoard = board.arBoard
    if bitLength(checkers) == 1:

        # Captures of checking pieces (except by king, which we will test later)
        chkcord = firstBit (checkers)
        b = getAttacks (board, chkcord, color) & ~kings
        for cord in iterBits(b):
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
                bits = moveArray[color == WHITE and BPAWN or PAWN][ep] & pawns
                for cord in iterBits (bits):
                    if not pinnedOnKing (board, cord, color):
                        yield newMove (cord, ep, ENPASSANT)
        
        # Lets block/capture the checking piece
        if sliders[arBoard[chkcord]]:
            bits = clearBit(fromToRay[kcord][chkcord], chkcord)
            
            for cord in iterBits (bits):
                b = getAttacks (board, cord, color)
                b &= ~(kings | pawns)
                
                # Add in pawn advances
                if color == WHITE and cord > H2:
                    if bitPosArray[cord-8] & pawns:
                        b |= bitPosArray[cord-8]
                    if cord >> 3 == 3 and arBoard[cord-8] == EMPTY and \
                            bitPosArray[cord-16] & pawns:
                        b |= bitPosArray[cord-16]
                
                elif color == BLACK and cord < H7:
                    if bitPosArray[cord+8] & pawns:
                        b |= bitPosArray[cord+8]
                    if cord >> 3 == 4 and arBoard[cord+8] == EMPTY and \
                            bitPosArray[cord+16] & pawns:
                        b |= bitPosArray[cord+16]
                
                for fcord in iterBits (b):
                    # If the piece is blocking another attack, we cannot move it
                    if pinnedOnKing (board, fcord, color):
                        continue
                    if arBoard[fcord] == PAWN and (cord > H7 or cord < A2):
                        for move in newPromotes (fcord, cord):
                            yield move
                    else:
                        yield newMove (fcord, cord)
    
    # If more than one checkers, move king to get out of check
    if checkers:
        escapes = moveArray[KING][kcord] & ~board.friends[color]
    else: escapes = 0
    
    for chkcord in iterBits (checkers):
        dir = directions[chkcord][kcord]
        if sliders[arBoard[chkcord]]:
            escapes &= ~rays[chkcord][dir]
            
    for cord in iterBits (escapes):
        if not isAttacked (board, cord, opcolor):
            yield newMove (kcord, cord)

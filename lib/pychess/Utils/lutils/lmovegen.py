
from bitboard import *
from attack import *
from pychess.Utils.const import *
from lmove import newMove

def newPromotes (fromcord, tocord):
    for p in KNIGHT_PROMOTION, BISHOP_PROMOTION, \
             ROOK_PROMOTION, QUEEN_PROMOTION:
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
    for cord in iterBits(knights):
        for move in bitsToMoves (cord, knightMoves[cord] & notfriends):
            yield move
    
    # King
    kingMoves = moveArray[KING]
    cord = firstBit( kings )
    for move in bitsToMoves (cord, kingMoves[cord] & notfriends):
        yield move
    
    # Rooks
    for cord in iterBits(rooks):
        attackBoard = rookAttack(board, cord)
        for move in bitsToMoves (cord, attackBoard & notfriends):
            yield move
    
    # Bishops
    for cord in iterBits(bishops):
        attackBoard = bishopAttack(board, cord)
        for move in bitsToMoves (cord, attackBoard & notfriends):
            yield move
    
    # Queens
    for cord in iterBits(queens):
        attackBoard = queenAttack(board, cord)
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
    
    if board.color == WHITE:
        if board.castling & W_OO and not fromToRay[E1][G1] & blocker and \
            not isAttacked (board, E1, BLACK) and \
            not isAttacked (board, F1, BLACK) and \
            not isAttacked (board, G1, BLACK):
                yield newMove (E1, G1, KING_CASTLE)
        
        if board.castling & W_OOO and not fromToRay[E1][B1] & blocker and \
            not isAttacked (board, E1, BLACK) and \
            not isAttacked (board, D1, BLACK) and \
            not isAttacked (board, C1, BLACK):
                yield newMove (E1, C1, QUEEN_CASTLE)
    
    else:
        if board.castling & B_OO and not fromToRay[E8][G8] & blocker and \
            not isAttacked (board, E8, WHITE) and \
            not isAttacked (board, F8, WHITE) and \
            not isAttacked (board, G8, WHITE):
                yield newMove (E8, G8, KING_CASTLE)
                
        if board.castling & B_OOO and not fromToRay[E8][B8] & blocker and \
            not isAttacked (board, E8, WHITE) and \
            not isAttacked (board, D8, WHITE) and \
            not isAttacked (board, C8, WHITE):
                yield newMove (E8, C8, QUEEN_CASTLE)

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
    
    # Rooks
    for cord in iterBits(rooks):
        attackBoard = rookAttack(board, cord)
        for move in bitsToMoves (cord, attackBoard & enemies):
            yield move
    
    # Bishops
    for cord in iterBits(bishops):
        attackBoard = bishopAttack(board, cord)
        for move in bitsToMoves (cord, attackBoard & enemies):
            yield move
    
    # Queens
    for cord in iterBits(queens):
        attackBoard = queenAttack(board, cord)
        for move in bitsToMoves (cord, attackBoard & enemies):
            yield move
    
    # White pawns
    pawnEnemies = enemies | (enpassant != None and bitPosArray[enpassant] or 0)
    
    if board.color == WHITE:
        
        # Promotes
        
        movedpawns = (pawns >> 8) & notblocker & rankBits[7]
        for cord in iterBits(movedpawns):
            for move in newPromotes (cord-8, cord):
                yield move
        
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
        for cord in iterBits(movedpawns):
            for move in newPromotes (cord+8, cord):
                yield move
        
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

################################################################################
#   Generate moves which doesn't capture any pieces                            #
################################################################################

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
    
    # Rooks
    for cord in iterBits(rooks):
        attackBoard = rookAttack(board, cord)
        for move in bitsToMoves (cord, attackBoard & notblocker):
            yield move
    
    # Bishops
    for cord in iterBits(bishops):
        attackBoard = bishopAttack(board, cord)
        for move in bitsToMoves (cord, attackBoard & notblocker):
            yield move
    
    # Queens
    for cord in iterBits(queens):
        attackBoard = queenAttack(board, cord)
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
    
    if board.color == WHITE:
        if board.castling & W_OO and not fromToRay[E1][G1] & blocker and \
            not isAttacked (board, E1, BLACK) and \
            not isAttacked (board, F1, BLACK) and \
            not isAttacked (board, G1, BLACK):
                yield newMove (E1, G1, KING_CASTLE)
        
        if board.castling & W_OOO and not fromToRay[E1][B1] & blocker and \
            not isAttacked (board, E1, BLACK) and \
            not isAttacked (board, D1, BLACK) and \
            not isAttacked (board, C1, BLACK):
                yield newMove (E1, C1, QUEEN_CASTLE)
    
    else:
        if board.castling & B_OO and not fromToRay[E8][G8] & blocker and \
            not isAttacked (board, E8, WHITE) and \
            not isAttacked (board, F8, WHITE) and \
            not isAttacked (board, G8, WHITE):
                yield newMove (E8, G8, KING_CASTLE)
                
        if board.castling & B_OOO and not fromToRay[E8][B8] & blocker and \
            not isAttacked (board, E8, WHITE) and \
            not isAttacked (board, D8, WHITE) and \
            not isAttacked (board, C8, WHITE):
                yield newMove (E8, C8, QUEEN_CASTLE)

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

################################################################################
#   Validate move                                                              #
################################################################################

def validate (board, move):
    
    fcord = (move >> 6) & 63
    
    fpiece = board.arBoard[fcord]
    
    # Empty from square  
    if fpiece == EMPTY:
        return False
    
    color = board.color
    friends = board.friends[color]
    
    # Piece is not right color  
    if not bitPosArray[fcord] & friends:
        return False
    
    tcord = move & 63
    
    # TO square is a friendly piece, so illegal move  
    if bitPosArray[tcord] & board.friends[color]:
        return False
    
    flag = move >> 12
    
    # If promotion move, piece must be pawn 
    if flag in (QUEEN_PROMOTION, ROOK_PROMOTION, BISHOP_PROMOTION,
                KNIGHT_PROMOTION, ENPASSANT) and fpiece != PAWN:
        return False
    
    # If enpassant, then the enpassant square must be correct 
    if flag == ENPASSANT and tcord != board.enpassant:
        return False
    
    # If castling, then make sure its the king 
    if flag in (KING_CASTLE, QUEEN_CASTLE) and fpiece != KING:
        return False 
    
    blocker = board.blocker
    tpiece = board.arBoard[tcord]
    
    # Pawn moves need to be handled specially  
    if fpiece == PAWN:
        if flag == ENPASSANT:
            enemies = board.friends[1-color] | bitPosArray[board.enpassant]
        else: enemies = board.friends[1-color]
        if color == WHITE:
            if not moveArray[PAWN][fcord] & bitPosArray[tcord] & enemies and \
               not (tcord - fcord == 8 and tpiece == EMPTY) and \
               not (tcord - fcord == 16 and fcord >> 3 == 1 and \
               not fromToRay[fcord][tcord] & blocker):
                return False
        else:
            if not moveArray[BPAWN][fcord] & bitPosArray[tcord] & enemies and \
               not (tcord - fcord == 8 and tpiece == EMPTY) and \
               not (tcord - fcord == 16 and fcord >> 3 == 6 and \
               not fromToRay[fcord][tcord] & blocker):
                return False
    
    # King moves are also special, especially castling  
    elif fpiece == KING:
        if color == WHITE:
            if not moveArray[fpiece][fcord] & bitPosArray[tcord] and \
               \
               not (fcord == E1 and tcord == G1 and flag == KING_CASTLE and \
               not fromToRay[E1][G1] & blocker and \
               not isAttacked (board, E1, BLACK) and \
               not isAttacked (board, F1, BLACK)) and \
               \
               not (fcord == E1 and tcord == C1 and flag == QUEEN_CASTLE and \
               not fromToRay[E1][B1] & blocker and \
               not isAttacked (board, E1, BLACK) and \
               not isAttacked (board, D1, BLACK)):
                return False
        else:
            if not moveArray[fpiece][fcord] & bitPosArray[tcord] and \
               \
               not (fcord == E8 and tcord == G8 and flag == KING_CASTLE and \
               not fromToRay[E8][G8] & blocker and \
               not isAttacked (board, E8, WHITE) and \
               not isAttacked (board, F8, WHITE)) and \
               \
               not (fcord == E8 and tcord == C8 and flag == QUEEN_CASTLE and \
               not fromToRay[E8][B8] & blocker and \
               not isAttacked (board, E8, WHITE) and \
               not isAttacked (board, D8, WHITE)):
                return False
    
    # Other pieces are more easy
    else:
        if not moveArray[fpiece][fcord] & bitPosArray[tcord]:
            return False
    
    # If there is a blocker on the path from fcord to tcord, illegal move  
    if sliders [fpiece]:
        if clearBit(fromToRay[fcord][tcord], tcord) & blocker:
            return False
    
    return True

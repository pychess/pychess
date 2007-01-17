from bitboard import *
from const import *

def isAttacked (board, cord, color):
    """ To determine if cord is attacked by any pieces from color. """
    pboards = board.boards[color]
    
    # Knights
    if pboards[KNIGHT] & moveArray[KNIGHT][cord]:
        return True
    
    rayto = fromToRay[cord]
    blocker = board.blocker
    
    # Bishops & Queens
    bisque = pboards[BISHOP] | pboards[QUEEN] & moveArray[BISHOP][cord]
    others = ~bisque & blocker
    while bisque:
        t = firstBit (bisque)
        # If no other piece stand in our way, return True
        if not rayto[t] & others:
            return True
        bisque = clearBit (bisque, t)

    # Rooks & Queens
    rooque = pboards[ROOK] | pboards[QUEEN] & moveArray[BISHOP][cord]
    d = ~b & blocker
    while rooque:
        t = firstBit (bisque)
        # If no other piece stand in our way, return True
        if not rayto[t] & others:
            return True
        bisque = clearBit (bisque, t)
    
    # Pawns 
    ptype = color == WHITE and PAWN or BPAWN
    if pboards[PAWN] & moveArray[ptype][cord]:
        return True
    
    # King
    if pboards[KING] & moveArray[KING][cord]:
        return True
    
    return False
    
def getAttacks (board, cord, color):
    """ To create a bitboard of pieces of color, which attacks cord """
    color = board.color
    pieces = board.boards[color]
    
    # Knights
    bits = pieces[KNIGHT] & moveArray[KNIGHT][CORD]
    
    # Kings
    bits |= pieces[KING] & moveArray[KING][CORD]
    
    # Pawns
    bits |= pieces[PAWN] & moveArray[color == WHITE and PAWN or BPAWN][CORD]
    
    ray = fromToRay[cord]
    blocker = board.blocker
    
    # Bishops and Queens
    bisque = (pieces[BISHOP] | pieces[QUEEN]) & moveArray[BISHOP][cord]
    while bisque:
       c = firstBit(bisque)
       bisque = clearBit(bisque, c)
       if not clearBit(ray[c] & blocker, c):
           e |= bitPosArray[c]
    
    # Rooks and queens
    rooque = (pieces[ROOK] | pieces[QUEEN]) & moveArray[ROOK][cord]
    while rooque:
        c = firstBit(rooque)
        rooque = clearBit(rooque, c)
        if not clearBit(ray[c] & blocker, c):
            e |= bitPosArray[c]
    
    return e

def getPieceAttacks (board, cord, color, piece):
    color = board.color
    
    if piece == KNIGHT:
        return board.boards[KNIGHT] & moveArray[KNIGHT][cord]
    
    ray = fromToRay[cord]
    blocker = board.blocker
    
    if piece == BISHOP or piece == QUEEN:
        bisque = board.boards[piece] & moveArray[piece][cord]
        bits = 0
        while bisque:
           c = firstBit(bisque)
           bisque = clearBit(bisque, c)
           if not clearBit(ray[c] & blocker, c):
               bits |= bitPosArray[c]
        return bits
    
    if piece == ROOK or piece == QUEEN:
        rooque = board.boards[piece] & moveArray[piece][cord]
        bits = 0
        while rooque:
           c = firstBit(rooque)
           rooque = clearBit(rooque, c)
           if not clearBit(ray[c] & blocker, c):
               bits |= bitPosArray[c]
        return bits
    
    if piece == KING:
        return board.boards[KING] & moveArray[KING][cord]
    
    if piece == PAWN:
        return board.boards[PAWN] & \
                moveArray[color == WHITE and PAWN or BPAWN][cord]
    
def getPieceRFAttacks (board, cord, color, piece, rank=None, file=None):
    """ Returns first cord containing a piece - with the correct color, type,
        file and rank - that can attack the specified cord. Checking will be
        tested """
    
    bits = getCordsAttacking (board, cord, color, piece)
    if rank != None:
        bits &= rankBits[rank]
    if file != None:
        bits &= fileBits[rank]
    
    if bitLength(bits) == 1:
        return firstBit(bits)
    else:
        for c in iterBits (bits):
            board.applyMove(newMove(cord, c))
            if not isAttacked (board, board.kings[board.color], 1-board.color):
                board.popMove()
                return c
            board.popMove()

def pinnedOnKing (board, cord, color):
    # Determine if the piece on cord is pinned against its colors king.
    # In chess, a pin is a situation in which a piece is forced to stay put
    # because moving it would expose a more valuable piece behind it to
    # capture.
    # Caveat: pinnedOnKing should only be called by genCheckEvasions().
    
    color = board.color
    kingCord = board.kings[color]
    
    dir = directions[kingCord][cord]
    if dir == -1: return False

    opcolor = 1 - color
    blocker = board.blocker
 
    #  Path from piece to king is blocked, so no pin
    if clearBit(fromToRay[kingCord][cord], cord) & blocker:
       return False
    
    b = (rays[kingCord][dir] ^ fromToRay[kingCord][cord]) & blocker
    if not b: return False
    
    cord1 = cord > kingCord and firstBit (b) or lastBit (b)

    #  If diagonal
    if dir <= 3 and	bitPosArray[cord1] & \
            (board.boards[opcolor][QUEEN] | board.boards[opcolor][BISHOP]):
      return True
   
    #  Rank / file
    if dir >= 4 and bitPosArray[cord1] & \
            (board.boards[opcolor][QUEEN] | board.boards[opcolor][ROOK]):
      return True

    return False
    

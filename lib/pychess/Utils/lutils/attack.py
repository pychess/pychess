from bitboard import *
from ldata import *
from pychess.Utils.const import *

#
# Caveat: Many functions in this module has very similar code. If you fix a
# bug, or write a perforance enchace, please update all functions. Apologies
# for the inconvenience
#

def isAttacked (board, cord, color):
    """ To determine if cord is attacked by any pieces from color. """
    pboards = board.boards[color]
    
    # Knights
    if pboards[KNIGHT] & moveArray[KNIGHT][cord]:
        return True
    
    rayto = fromToRay[cord]
    blocker = board.blocker
    
    # Bishops & Queens
    bisque = (pboards[BISHOP] | pboards[QUEEN]) & moveArray[BISHOP][cord]
    others = ~bisque & blocker
    for t in iterBits(bisque):
        # If there is a path and no other piece stand in our way
        ray = rayto[t]
        if ray and not ray & others:
            return True

    # Rooks & Queens
    rooque = (pboards[ROOK] | pboards[QUEEN]) & moveArray[ROOK][cord]
    others = ~rooque & blocker
    for t in iterBits(rooque):
        # If there is a path and no other piece stand in our way
        ray = rayto[t]
        if ray and not ray & others:
            return True
    
    # Pawns
    # Would a pawn of the opposite color, standing at out kings cord, be able
    # to attack any of our pawns?
    ptype = color == WHITE and BPAWN or PAWN
    if pboards[PAWN] & moveArray[ptype][cord]:
        return True
    
    # King
    if pboards[KING] & moveArray[KING][cord]:
        return True
    
    return False
    
def getAttacks (board, cord, color):
    """ To create a bitboard of pieces of color, which attacks cord """
    
    pieces = board.boards[color]
    
    # Knights
    bits = pieces[KNIGHT] & moveArray[KNIGHT][cord]
    
    # Kings
    bits |= pieces[KING] & moveArray[KING][cord]
    
    # Pawns
    bits |= pieces[PAWN] & moveArray[color == WHITE and BPAWN or PAWN][cord]
    
    rayto = fromToRay[cord]
    blocker = board.blocker
    
    # Bishops and Queens
    bisque = (pieces[BISHOP] | pieces[QUEEN]) & moveArray[BISHOP][cord]
    for c in iterBits(bisque):
        ray = rayto[c]
        if ray and not clearBit(ray & blocker, c):
            bits |= bitPosArray[c]
    
    # Rooks and queens
    rooque = (pieces[ROOK] | pieces[QUEEN]) & moveArray[ROOK][cord]
    for c in iterBits(rooque):
        ray = rayto[c]
        if ray and not clearBit(ray & blocker, c):
            bits |= bitPosArray[c]
    
    return bits

def getPieceMoves (board, cord, color, piece):
    """ To create a bitboard of specified pieces of color, which can move to
        cord """
    
    color = board.color
    pieces = board.boards[color]
    
    if piece == KNIGHT or piece == KING:
        return pieces[piece] & moveArray[piece][cord]
    
    rayto = fromToRay[cord]
    blocker = board.blocker
    
    if sliders[piece]:
        cords = pieces[piece] & moveArray[piece][cord]
        bits = 0
        for c in iterBits(cords):
            ray = rayto[c]
            if ray and not clearBit(ray & blocker, c):
                bits |= bitPosArray[c]
        return bits
    
    if piece == PAWN:
        pawns = pieces[PAWN]
        bits = pawns & moveArray[color == WHITE and BPAWN or PAWN][cord]
        bits |= pawns & bitPosArray[cord + (color == WHITE and -8 or 8)]
        if not blocker & bitPosArray[cord + (color == WHITE and -8 or 8)]:
            bits |= pawns & rankBits[color == WHITE and 1 or 6]
        return bits

def pinnedOnKing (board, cord, color):
    # Determine if the piece on cord is pinned against its colors king.
    # In chess, a pin is a situation in which a piece is forced to stay put
    # because moving it would expose a more valuable piece behind it to
    # capture.
    # Caveat: pinnedOnKing should only be called by genCheckEvasions().
    
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

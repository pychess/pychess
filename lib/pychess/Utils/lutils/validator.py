from lmove import *
from pychess.Utils.const import *
from bitboard import *
from attack import *

################################################################################
#   Validate move                                                              #
################################################################################

def validateMove (board, move):
    
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
    if (flag in PROMOTIONS or flag == ENPASSANT) and fpiece != PAWN:
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
               not (tcord - fcord == -8 and tpiece == EMPTY) and \
               not (tcord - fcord == -16 and fcord >> 3 == 6 and \
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
    
################################################################################
#   Validate board                                                             #
################################################################################

def validateBoard (board):
    """ Check the board to make sure that its valid.  Some things to check are
        a.  Both sides have max 1 king and max 8 pawns
        b.  Side not on the move must not be in check.
        c.  If en passant square is set, check it is possible.
        d.  Check if castling status are all correct. """
    
    #
    # TODO: This functions hasn't yet been translated from C to Python
    #       Not fully at least
    #
    
    # You must place both a Black King and White King on the board
    if nbits (board.b[WHITE][KING]) != 1:
        return False
    if nbits (board.b[BLACK][KING]) != 1:
        return False
    
    # You can't place a pawn on the eight rank
    if board.b[WHITE][PAWN] & rankBits[7]:
        return False
    if board.b[BLACK][PAWN] & rankBits[0]:
        return False
    
    # You can't set up a position in which a side has more than eight pawns
    if nbits(board.b[WHITE][PAWN]) > 8:
        return False
    if nbits(board.b[BLACK][PAWN]) > 8:
        return False
    
    # You can't set up a position in which one side's King is in check and the
    # other side is to move (otherwise it's a position in which mate has
    # already been delivered)
    side = board.side;
    xside = 1^side;
    if SqAtakd (board.king[xside], side):
        return False
    
    if board.ep > -1:
        sq = board.ep + (xside == WHITE and 8 or -8)
        if not BitPosArray[sq] & board.b[xside][PAWN]:
            return False
    
    if board.flag & WKINGCASTLE:
        if not(BitPosArray[E1] & board.b[WHITE][KING]):
            return False
        if not(BitPosArray[H1] & board.b[WHITE][ROOK]):
            return False
    
    if board.flag & WQUEENCASTLE:
        if not(BitPosArray[E1] & board.b[WHITE][KING]):
            return False
        if not(BitPosArray[A1] & board.b[WHITE][ROOK]):
            return False
    
    if board.flag & BKINGCASTLE:
        if not(BitPosArray[E8] & board.b[BLACK][KING]):
            return False
        if not(BitPosArray[H8] & board.b[BLACK][ROOK]):
            return False
    
    if board.flag & BQUEENCASTLE:
        if not(BitPosArray[E8] & board.b[BLACK][KING]):
            return False
        if not(BitPosArray[A8] & board.b[BLACK][ROOK]):
            return False
    
    return True

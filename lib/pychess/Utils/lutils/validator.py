from pychess.Utils.const import *
from pychess.Utils.lutils.attack import isAttacked
from pychess.Utils.lutils.bitboard import bitPosArray, clearBit
from pychess.Utils.lutils.ldata import moveArray, fromToRay
from pychess.Utils.lutils.lmovegen import genCastles

################################################################################
#   Validate move                                                              #
################################################################################

def validateMove (board, move):
    flag = move >> 12
    fcord = (move >> 6) & 63
    tcord = move & 63

    if flag == DROP:
        tpiece = board.arBoard[tcord]
        if tpiece != EMPTY:
            return False
        else:
            if fcord == PAWN:
                rank = tcord >> 3
                return rank > 0 and rank < 7
            else:
                return True
    
    fpiece = board.arBoard[fcord]
    
    # Empty from square  
    if fpiece == EMPTY:
        return False
    
    color = board.color
    friends = board.friends[color]
    
    # Piece is not right color  
    if not bitPosArray[fcord] & friends:
        return False
    
    # TO square is a friendly piece, so illegal move  
    if bitPosArray[tcord] & board.friends[color]:
        if board.variant == FISCHERRANDOMCHESS:
            if not flag in (KING_CASTLE, QUEEN_CASTLE):
                return False
        else:
            return False
    
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
        enemies = board.friends[1-color]
        if flag == ENPASSANT:
            enemies |= bitPosArray[board.enpassant]
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
        if board.variant == FISCHERRANDOMCHESS:
            from pychess.Variants.fischerandom import frc_castling_move
            if not (moveArray[fpiece][fcord] & bitPosArray[tcord] and \
                    not flag in (KING_CASTLE, QUEEN_CASTLE)) and \
               not frc_castling_move(board, fcord, tcord, flag):
                return False
        elif board.variant in (WILDCASTLECHESS, WILDCASTLESHUFFLECHESS):
            if not (moveArray[fpiece][fcord] & bitPosArray[tcord] and \
                    not flag in (KING_CASTLE, QUEEN_CASTLE)) and \
               not move in genCastles(board):
                return False
        else:
            if board.variant == ATOMICCHESS and tpiece:
                return False
            if not (moveArray[fpiece][fcord] & bitPosArray[tcord] and \
                    not flag in (KING_CASTLE, QUEEN_CASTLE)) and \
               not move in genCastles(board):
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

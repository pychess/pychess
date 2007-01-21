def RANK (cord): return cord >> 3
def FILE (cord): return cord & 7
def FLAG (move): return move >> 12
def PROMOTE_PIECE (move): return FLAG(move) -3

from attack import *
from lmovegen import *

def toSAN (board, move, fan=False):
    """ Returns a Short/Abbreviated Algebraic Notation string of a move 
        The board should be prior to the move """
    
    flag = move >> 12
    
    if flag == KING_CASTLE:
        return "O-O"
    elif flag == QUEEN_CASTLE:
        return "O-O-O"
    
    fcord = (move >> 6) & 63
    tcord = move & 63
    
    fpiece = board.arBoard[fcord]
    tpiece = board.arBoard[tcord]
    
    part0 = ""
    part1 = ""
    
    if fan:
        part0 += fandic[board.color][fpiece]
    elif fpiece != PAWN:
    	part0 += reprSign[fpiece]
    
    part1 = reprCord[tcord]
    
    if not fpiece in (PAWN, KING):
        pieces = getPieceAttacks (board, tcord, board.color, piece)
        
        if bitLength(pieces) > 1:
            xs = []
            ys = []
            for cord in iterBits(pieces):
                xs.append(cord & 7)
                ys.append(cord >> 3)
                # Checking and stuff            

    if tpiece != EMPTY:
        part1 = "x" + part1
        if fpiece == PAWN:
            part0 += reprRank[fcord & 7]
    
    notat = part0 + part1
    if flag == QUEEN_PROMOTION:
        notat += "="+reprSign[QUEEN]
    elif flag == ROOK_PROMOTION:
        notat += "="+reprSign[ROOK]
    elif flag == BISHOP_PROMOTION:
        notat += "="+reprSign[BISHOP]
    elif flag == KNIGHT_PROMOTION:
        notat += "="+reprSign[KNIGHT]
        
    return notat

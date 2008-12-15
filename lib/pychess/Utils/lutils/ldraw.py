from bitboard import bitLength
from ldata import BLACK_SQUARES
from pychess.Utils.const import *

def testRepetition (board):
    if len(board.history) >= 8:
        if board.history[-4] != None and board.history[-8] != None and \
                board.hash == board.history[-4][4] == board.history[-8][4]:
            return True
    return False

def testFifty (board):
    if board.fifty >= 100:
        return True
    return False

drawSet = set((
    (0, 1, 0, 0,   0, 0, 0, 0), #KBK
    (1, 0, 0, 0,   0, 0, 0, 0), #KNK
    (0, 0, 0, 0,   0, 1, 0, 0), #KKB
    (0, 0, 0, 0,   1, 0, 0, 0), #KNK
    
    (1, 0, 0, 0,   0, 1, 0, 0), #KNKB
    (0, 1, 0, 0,   1, 0, 0, 0), #KBKN
))

# Contains not 100% sure ones 
drawSet2 = set((
    (2, 0, 0, 0,   0, 0, 0, 0), #KNNK
    (0, 0, 0, 0,   2, 0, 0, 0), #KKNN
    
    (2, 0, 0, 0,   1, 0, 0, 0), #KNNKN
    (1, 0, 0, 0,   2, 0, 0, 0), #KNKNN
    (2, 0, 0, 0,   0, 1, 0, 0), #KNNKB
    (0, 1, 0, 0,   2, 0, 0, 0), #KBKNN
    (2, 0, 0, 0,   0, 0, 1, 0), #KNNKR
    (0, 0, 1, 0,   2, 0, 0, 0)  #KRKNN
))

def testMaterial (board):
    """ Tests if no players are able to win the game from the current
        position """
    
    whiteBoards = board.boards[WHITE]
    blackBoards = board.boards[BLACK]
    
    if bitLength(whiteBoards[PAWN]) or bitLength(blackBoards[PAWN]):
        return False
    
    if bitLength(whiteBoards[QUEEN]) or bitLength(blackBoards[QUEEN]):
        return False
    
    wn = bitLength(whiteBoards[KNIGHT])
    wb = bitLength(whiteBoards[BISHOP])
    wr = bitLength(whiteBoards[ROOK])
    bn = bitLength(blackBoards[KNIGHT])
    bb = bitLength(blackBoards[BISHOP])
    br = bitLength(blackBoards[ROOK])
    
    if (wn, wb, wr, 0,   bn, wb, wr, 0) in drawSet:
        return True
        
    # Tests KBKB. Draw if bishops are of same color
    if not wn + wr + bn + wr and wb == 1 and bb == 1:
        if whiteBoards[BISHOP] & BLACK_SQUARES and True != \
           blackBoards[BISHOP] & BLACK_SQUARES and True:
            return True

# This could be expanded by the fruit kpk draw function, which can test if a
# certain king verus king and pawn posistion is winable.

def test (board):
    return testRepetition (board) or \
           testFifty (board) or \
           testMaterial (board)

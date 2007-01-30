from bitboard import bitLength
from ldata import BLACK_SQUARES
from pychess.Utils.const import *

def testRepetition (board):
    if len(board.history) >= 5:
        if board.history[-2] != None and board.history[-4] != None and \
                board.hash == board.history[-2][4] == board.history[-4][4]:
            return True
    return False

def testFifty (board):
    if board.fifty >= 50:
        return True
    return False

def testMaterial (board):
    """ Tests if no players are able to win the game from the current
        position """
    
    whiteBoards = board.boards[WHITE]
    blackBoards = board.boards[BLACK]
    
    if bitLength(whiteBoards[QUEEN]) > 0 or bitLength(whiteBoards[ROOK]) or \
            bitLength(blackBoards[QUEEN]) > 0 or bitLength(blackBoards[ROOK]):
        return False
    
    wp = bitLength(whiteBoards[PAWN])
    bp = bitLength(blackBoards[PAWN])
    if wp > 0 or bp > 0:
        return False
    
    wn = bitLength(whiteBoards[KNIGHT])
    wb = bitLength(whiteBoards[BISHOP])
    bn = bitLength(blackBoards[KNIGHT])
    bb = bitLength(blackBoards[BISHOP])
    
    # Tests: KK, KBK, KKB, KNK, KKN
    if wn + wb + bn + bb <= 1:
        return True
    
    # Tests KBKB
    if wn == 0 and bn == 0 and wb == 1 and bb == 1:
        # Draw if bishops are of same color
        if (whiteBoards[BISHOP] & BLACK_SQUARES and BLACK or WHITE) == \
                (blackBoards[BISHOP] & BLACK_SQUARES and BLACK or WHITE):
            return True

# This could be expanded by the fruit kpk draw function

""" This module contains chess logic functins for the pychess client. They are
    based upon the lutils modules, but supports standard object types and is
    therefore not as fast. """

from lutils import lmovegen
from lutils.lmove import FCORD, TCORD
from Cord import Cord
from Move import Move
from const import reprCord

def getDestinationCords (board, cord):
    tcords = []
    for move in lmovegen.genAllMoves (board.board):
        if FCORD(move) == cord.cord:
            if not board.willLeaveInCheck (Move(move)):
                tcords.append(Cord(TCORD(move)))
    return tcords

from lutils import ldraw
from const import *

def getStatus (board):
    
    # Test draw by insufficient material
    if ldraw.testMaterial (board.board):
        return DRAW, DRAW_INSUFFICIENT
    
    if ldraw.testRepetition (board.board):
        return DRAW, DRAW_REPITITION
    
    if ldraw.testFifty (board.board):
        return DRAW, DRAW_50MOVES
    
    moves = [move for move in lmovegen.genAllMoves (board.board)]
    
    if moves:
        return RUNNING
    
    if board.board.isChecked():
        if board.color == WHITE:
            reason = BLACKWON
        else: reason = WHITEWON
        return MATE, reason
    
    return DRAW, DRAW_STALEMATE

def validate (board, move):
    return lmovegen.validate(board.board, move.move)

""" This module contains chess logic functins for the pychess client. They are
    based upon the lutils modules, but supports standard object types and is
    therefore not as fast. """

from lutils import lmovegen
from lutils.validator import validateMove
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
    
    lboard = board.board
    
    # Test draw by insufficient material
    if ldraw.testMaterial (lboard):
        return DRAW, DRAW_INSUFFICIENT
    
    if ldraw.testRepetition (lboard):
        return DRAW, DRAW_REPITITION
    
    if ldraw.testFifty (lboard):
        return DRAW, DRAW_50MOVES
    
    lboard.lock.acquire()
    for move in lmovegen.genAllMoves (lboard):
        lboard.applyMove(move)
        if lboard.opIsChecked():
            lboard.popMove()
            continue
        lboard.popMove()
        lboard.lock.release()
        return RUNNING, UNKNOWN_REASON
    lboard.lock.release()
    
    if lboard.isChecked():
        if board.color == WHITE:
            status = BLACKWON
        else: status = WHITEWON
        return status, WON_MATE
    
    return DRAW, DRAW_STALEMATE

def validate (board, move):
    return validateMove (board.board, move.move)

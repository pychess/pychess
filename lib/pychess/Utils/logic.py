""" This module contains chess logic functins for the pychess client. They are
    based upon the lutils modules, but supports standard object types and is
    therefore not as fast. """

from lutils import lmovegen
from lutils.validator import validateMove
from lutils.lmove import FCORD, TCORD
from lutils import ldraw
from Cord import Cord
from Move import Move
from const import *
from lutils.bitboard import iterBits
from lutils.attack import getAttacks

def getDestinationCords (board, cord):
    tcords = []
    for move in lmovegen.genAllMoves (board.board):
        if FCORD(move) == cord.cord:
            if not board.willLeaveInCheck (Move(move)):
                tcords.append(Cord(TCORD(move)))
    return tcords

def isClaimableDraw (board):
    lboard = board.board
    if ldraw.testRepetition (lboard):
        return True
    if ldraw.testFifty (lboard):
        return True
    return False

def getStatus (board):
    
    lboard = board.board
    
    if ldraw.testMaterial (lboard):
        return DRAW, DRAW_INSUFFICIENT
    
    if ldraw.testRepetition (lboard):
        return RUNNING, DRAW_REPITITION
    
    if ldraw.testFifty (lboard):
        return RUNNING, DRAW_50MOVES
    
    lboard.lock.acquire()
    try:
        for move in lmovegen.genAllMoves (lboard):
            lboard.applyMove(move)
            if lboard.opIsChecked():
                lboard.popMove()
                continue
            lboard.popMove()
            return RUNNING, UNKNOWN_REASON
    finally:
        lboard.lock.release()
    
    if lboard.isChecked():
        if board.color == WHITE:
            status = BLACKWON
        else: status = WHITEWON
        return status, WON_MATE
    
    return DRAW, DRAW_STALEMATE

def validate (board, move):
    return validateMove (board.board, move.move)

def getMoveKillingKing (board):
    """ Returns a move from the current color, able to capture the opponent
        king """
    
    lboard = board.board
    color = lboard.color
    opking = lboard.kings[1-color]
    
    for cord in iterBits (getAttacks(lboard, opking, color)):
        return Move(Cord(cord), Cord(opking), board)

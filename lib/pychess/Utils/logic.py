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
from pychess.Variants.losers import testKingOnly


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

def playerHasMatingMaterial (board, playercolor):
    lboard = board.board
    return ldraw.testPlayerMatingMaterial(lboard, playercolor)

def getStatus (board):
    
    lboard = board.board

    if board.variant == LOSERSCHESS:
        if testKingOnly(lboard):
            if board.color == WHITE:
                status = WHITEWON
            else:
                status = BLACKWON
            return status, WON_NOMATERIAL
    else:
        if ldraw.testMaterial (lboard):
            return DRAW, DRAW_INSUFFICIENT
    
    if ldraw.testRepetition (lboard):
        return DRAW, DRAW_REPITITION
    
    if ldraw.testFifty (lboard):
        return DRAW, DRAW_50MOVES
    
    board_clone = lboard.clone()
    for move in lmovegen.genAllMoves (board_clone):
        board_clone.applyMove(move)
        if board_clone.opIsChecked():
            board_clone.popMove()
            continue
        board_clone.popMove()
        return RUNNING, UNKNOWN_REASON
    
    if lboard.isChecked():
        if board.variant == LOSERSCHESS:
            if board.color == WHITE:
                status = WHITEWON
            else:
                status = BLACKWON
        else:
            if board.color == WHITE:
                status = BLACKWON
            else:
                status = WHITEWON
        return status, WON_MATE
    
    if board.variant == LOSERSCHESS:
        if board.color == WHITE:
            status = WHITEWON
        else:
            status = BLACKWON
        return status, DRAW_STALEMATE
    else:
        return DRAW, DRAW_STALEMATE

def standard_validate (board, move):
    return validateMove (board.board, move.move) and \
           not board.willLeaveInCheck(move)

def validate (board, move):
    if board.variant == LOSERSCHESS:
        capture = board[move.cord1] != None
        if capture:
            return standard_validate (board, move)
        else:
            can_capture = False
            can_escape = False
            ischecked = board.board.isChecked()
            for c in lmovegen.genCaptures(board.board):
                can_capture = True
                if ischecked:
                    if not board.willLeaveInCheck(Move(c)):
                        can_escape = True
                        break
                else:
                    break
            if can_capture:
                if ischecked and not can_escape:
                    return standard_validate (board, move)
                else:
                    return False
            else:
                return standard_validate (board, move)
    
    else:
        return standard_validate (board, move)

def getMoveKillingKing (board):
    """ Returns a move from the current color, able to capture the opponent
        king """
    
    lboard = board.board
    color = lboard.color
    opking = lboard.kings[1-color]
    
    for cord in iterBits (getAttacks(lboard, opking, color)):
        return Move(Cord(cord), Cord(opking), board)

def genCastles (board):
    for move in lmovegen.genCastles(board.board):
        yield Move(move)

#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from pychess.Utils.Cord import Cord
from pychess.Utils.const import *
from lutils import lmove
from lutils.lmove import ParsingError

class Move:
    
    def __init__ (self, cord0, cord1=None, board=None, promotion=None):
        """ Inits a new highlevel Move object.
            The object can be initialized in the follow ways:
                Move(cord0, cord1, board, [promotionPiece])
                Move(lovLevelMoveInt) """
        
        if not cord1:
            self.move = cord0
            flag = self.move >> 12
            if flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                        BISHOP_PROMOTION, KNIGHT_PROMOTION):
                self.promotion = PROMOTE_PIECE (move)
            else: self.promotion = QUEEN
            self.cord0 = Cord(lmove.FCORD(self.move))
            self.cord1 = Cord(lmove.TCORD(self.move))
            
        else:
            self.cord0 = cord0
            self.cord1 = cord1
            
            if board[self.cord0] == PAWN and  self.cord1.y in (0,7):
                if promotion == None: promotion = QUEEN
                flag = promotion + 3
                
            elif board[self.cord0].sign == KING:
                if self.cord0.x - self.cord1.x == 2:
                    flag = QUEEN_CASTLE
                elif self.cord0.x - self.cord1.x == -2:
                    flag = KING_CASTLE
                    
            elif board[self.cord0].sign == PAWN and \
                    board[self.cord1] == None and \
                    self.cord0.x != self.cord1.x and \
                    self.cord0.y != self.cord1.y:
                flag = ENPASSANT
                
            elif board[self.cord1] != None:
                flag = CAPTURE
                
            else: flag = NORMAL_MOVE
            
            self.move = lmove.newMove(self.cord0.cord, self.cord1.cord, flag)
            
    def _get_cords (self):
        return (self.cord0, self.cord1)
    cords = property(_get_cords)
    
    def _get_promotion (self):
        flag = FLAG(self.move)
        if flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                    BISHOP_PROMOTION, KNIGHT_PROMOTION):
            return flag -3
        return None
    promotion = property(_get_promotion)
    
    def __repr__ (self):
        return str(self.cord0) + str(self.cord1)

    def __eq__ (self, other):
        if isinstance(other, Move):
            return other.cord0 == self.cord0 and \
                other.cord1 == self.cord1 and \
                other.promotion == self.promotion
    
    def __hash__ (self):
        return hash(self.cords)

def parseAny (board, algnot):
    type = determineAlgebraicNotation (algnot)
    if type == SAN:
        return parseSAN (board, algnot)
    if type == AN:
        return parseAN (board, algnot)
    if type == LAN:
        return parseLAN (board, algnot)
    return parseFAN (board, algnot)

def determineAlgebraicNotation (algnot):
    
    upnot = algnot.upper()
    
    if upnot in ("O-O-O", "O-O"):
        return SAN
    
    if "-" in algnot:
        return LAN
    
    if (len(algnot) == 4 or (len(algnot) == 5 and upnot[4] in reprSign)) and \
            algnot[:2] in cordDic and algnot[2:4] in cordDic:
        return AN
    
    if algnot[0] in FAN_PIECES[WHITE] or algnot[0] in FAN_PIECES[BLACK]:
        return FAN
    
    return SAN

################################################################################
# Parsers                                                                      #
################################################################################

def parseSAN (board, san):
    """ Parse a Short/Abbreviated Algebraic Notation string """
    
    return Move (lmove.parseSAN (board, san))

def parseLAN (board, lan):
    """ Parse a Long/Expanded Algebraic Notation string """
    
    return Move (lmove.parseLAN (board, lan))

def parseFAN (board, lan):
    """ Parse a Long/Expanded Algebraic Notation string """
    
    fans = FAN_PIECES[board.color]
    
    san = lan
    san = san.replace(fans[KING], "K")
    san = san.replace(fans[QUEEN], "Q")
    san = san.replace(fans[ROOK], "R")
    san = san.replace(fans[BISHOP], "B")
    san = san.replace(fans[KNIGHT], "N")
    san = san.replace(fans[PAWN])
    
    return Move(lmove.parseSAN (board, san))

def parseAN (board, an):
    """ Parse an Algebraic Notation string """
    
    return Move(lmove.parseAN (board, an))

################################################################################
# Exporters                                                                    #
################################################################################

def toAN (board, move):
    """ Returns a Algebraic Notation string of a move
        board should be prior to the move """
    
    return lmove.toAN (board, move.move)
    
def toSAN (board, move):
    """ Returns a Short/Abbreviated Algebraic Notation string of a move 
        The board should be prior to the move, board2 past.
        If not board2, toSAN will not test mate """
    
    return lmove.toSAN (board, move.move)

def toLAN (board, move):
    """ Returns a Long/Expanded Algebraic Notation string of a move
        board should be prior to the move """
    
    return lmove.toLAN (board, move.move)

def toFAN (board, move):
    """ Returns a Figurine Algebraic Notation string of a move """
    
    fans = FAN_PIECES[board.color]
    san = lmove.toSAN (board, san)
    
    lan = san
    if "K" in lan or "Q" in lan or "R" in lan or "B" in lan or "N" in lan:
        lan = lan.replace("K", fans[KING])
        lan = lan.replace("Q", fans[QUEEN])
        lan = lan.replace("R", fans[ROOK])
        lan = lan.replace("B", fans[BISHOP])
        lan = lan.replace("N", fans[KNIGHT])
    else:
        lan = fans[PAWN] + lan
    
    return lan

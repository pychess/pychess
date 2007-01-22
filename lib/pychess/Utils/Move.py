#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from pychess.Utils.Cord import Cord
from pychess.Utils.const import *

class ParsingError (Exception): pass

class Move:
    
    def __init__ (self, cord0, cord1=None, promotion=QUEEN):
        """ Inits a new highlevel Move object.
            The object can be initialized in the follow ways:
                Move(cord0, cord1, [promotion])
                Move(lovLevelMoveInt) """
        
        if not cord1:
            move = cord1
            flag = move >> 12
            if flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                        BISHOP_PROMOTION, KNIGHT_PROMOTION):
                self.promotion = PROMOTE_PIECE (move)
            else: self.promotion = QUEEN
            self.cord0 = Cord(move >> 6  & 63)
            self.cord1 = Cord(move & 63)
        
        else:
            self.cord0 = cord0
            self.cord1 = cord1
            self.promotion = promotion
    
    def _get_cords (self):
        return (self.cord0, self.cord1)
    cords = property(_get_cords)
    
    def __repr__ (self):
        return str(self.cord0) + str(self.cord1)

    def __eq__ (self, other):
        if isinstance(other, Move):
            return other.cord0 == self.cord0 and \
                other.cord1 == self.cord1 and \
                other.promotion == self.promotion
    
    def __hash__ (self):
        return hash(self.cords)
    
def parseSAN (board, san):
    """ Parse a Short/Abbreviated Algebraic Notation string """
    
    cord0 = None
    cord1 = None
    promotion = QUEEN
    
    notat = san
    notat = notat.replace("0","o").replace("O","o")
    notat = notat.replace("=","").replace("+","").replace("#","").replace("x","")
    notat = notat.strip()
    # only remove the "-" if no castling detected
    if notat != "o-o":
        if notat != "o-o-o":
            notat = notat.replace("-","")
    
    if not notat: raise ParsingError, "Unable to parse sanmove '%s'" % san
    
    c = notat[-1].lower()
    if c in ("q", "r", "b", "n"):
        promotion = chr2Sign[c]
        notat = notat[:-1]
    color = board.color
    
    if notat.startswith("o-o"):
        if color == WHITE:
            row = 0
        else: row = 7
        cord0 = Cord(4, row)
        if notat == "o-o":
            cord1 = Cord(6, row)
        else:
            cord1 = Cord(2, row)
        return movePool.pop (cord0, cord1, promotion)

    if "x" in notat:
        since, then = notat.split("x")
        cord1 = Cord(then)
        notat = since

    sign = PAWN
    if notat[0] in ("Q", "R", "B", "K", "N"):
        sign = chr2Sign[notat[0].lower()]
        notat = notat[1:]    

    row = None
    col = None
    if notat and len(notat) != 2 and notat[0] in ("a","b","c","d","e","f","g","h"):
        col = ord(notat[0]) - ord("a")
        notat = notat[1:]
    if notat and notat[0] in ("1","2","3","4","5","6","7","8"):
        row = int(notat[0])-1
        notat = notat[1:]
    
    if notat:
        try:
            cord1 = Cord(notat)
        except: raise ParsingError, "Unable to parse sanmove %s" % san
    
    bits = getPieceRFAttacks (board, cord1.cord, color, sign, row, col)
    cord0 = firstBit(bits)
    if not cord0:
        raise ParsingError, "Unable to parse sanmove %s" % san
    
    return movePool.pop (Cord(cord0), cord1, promotion)
    
def parseLAN (board, lan):
    """ Parse a Long/Expanded Algebraic Notation string """
    
    if not lan: raise ParsingError, "Unable to parse lanmove '%s'" % lan
    
    lan = lan.lower()
    if lan.startswith("o-o"):
        color = board.color
        if color == WHITE: row = 0
        else: row = 7
        cord0 = Cord(4, row)
        if lan == "o-o": cord1 = Cord(6, row)
        else: cord1 = Cord(2, row)
        return movePool.pop (cord0, cord1)
    
    promotion = QUEEN
    
    if lan.find("-") >= 0:
        c0, c1 = lan.split("-")
    elif lan.find("x") >= 0:
        c0, c1 = lan.split("x")
    else: raise ParsingError, "Unable to parse lanmove %s.\
                               It should contain '-' or 'x'" % lan
    
    if len(c0) == 3: c0 = c0[1:]
    
    if len(c1) > 2:
        c1 = c1[:2]
        try:
            promotion = chr2Sign[c1[-1]]
        except KeyError:
            raise ParsingError, "Unable to parse lanmove %s" % lan
    
    try:
        c0 = Cord(c0)
        c1 = Cord(c1)
    except:
        raise ParsingError, "Unable to parse lanmove %s" % lan
    
    return movePool.pop (Cord(c0), Cord(c1), promotion)

def parseAN (board, an):
    """ Parse an Algebraic Notation string """
    if not 4 <= len(an) <= 5:
        raise ParsingError, "Bad an move, %s. Wrong size" % an
    try:
        c0 = Cord(an[:2])
        c1 = Cord(an[2:4])
    except:
        raise ParsingError, "Bad an move, %s" % an
        
    if len(an) == 5:
        return movePool.pop(c0, c1, chr2Sign[an[4].lower()])
    return movePool.pop(c0, c1)

fandic = [
    ["♔", "♕", "♖", "♗", "♘", "♙"],
    ["♚", "♛", "♜", "♝", "♞", "♟"]
]

def toSAN (board, board2, move, fan=False):
    """ Returns a Short/Abbreviated Algebraic Notation string of a move 
        The board should be prior to the move, board2 past.
        If not board2, toSAN will not test mate """
    
    c0, c1 = move.cords
    if board[c0].sign == KING:
        if c0.x - c1.x == 2:
            return "O-O-O"
        elif c0.x - c1.x == -2:
            return "O-O"
    
    part0 = ""
    part1 = ""
    
    if fan:
        part0 += fandic[board.color][board[c0].sign]
    elif board[c0].sign != PAWN:
    	part0 += reprSign[board[c0].sign][0]
        
    part1 = str(c1)
    
    if not board[c0].sign in (PAWN, KING):
        xs = []
        ys = []
        
        if board.movelist != None:
            for cord0, cord1s in board.movelist.iteritems():
                if move.cord1 in cord1s and not cord0.__eq__(move.cord0) and \
                        board[cord0].sign == board[move.cord0].sign:
                    xs.append(cord0.x)
                    ys.append(cord0.x)
        else:
            for y, row in enumerate(board.data):
                for x, piece in enumerate(row):
                    if not piece: continue
                    if piece.sign != board[c0].sign: continue
                    if piece.color != board[c0].color: continue
                    if y == c0.y and x == c0.x: continue
                    cord0 = Cord(x, y)
                    mov = movePool.pop(cord0, move.cord1)
                    from validator import validate
                    if validate (mov, board, False):
                        xs.append(cord0.x)
                        ys.append(cord0.x)
                    movePool.add(mov)

        if xs or ys:
            if not move.cord0.y in ys and not move.cord0.x in xs:
                part0 += move.cord0.cx
            elif move.cord0.y in ys and not move.cord0.x in xs:
                part0 += move.cord0.cx
            elif move.cord0.x in xs and not move.cord0.y in ys:
                part0 += move.cord0.cy
            else: part0 += str(move.cord0)
            

    if board[c1] != None:
        part1 = "x" + part1
        if board[c0].sign == PAWN:
            part0 += c0.cx
    
    notat = part0 + part1
    if board[c0].sign == PAWN and c1.y in [0,7]:
        notat += "=" + reprSign[move.promotion]
    
    from pychess.Utils import validator
    board2.color = 1 - board2.color
    if board2:
        if board2.status in (WHITEWON, BLACKWON):
            notat += "#"
        elif validator.isCheck(board2, 1-board2.color):
            notat += "+"
    else:
        board2 = board.move(move)
        if validator.isCheck(board2, 1-board2.color):
            notat += "+"
    board2.color = 1 - board2.color
    
    return notat

def toLAN (board, move):
    """ Returns a Long/Expanded Algebraic Notation string of a move
        board should be prior to the move """
    
    s = str(move.cord0) + "-" + str(move.cord1)
    if board[move.cord0].sign != PAWN:
        s = reprSign[board[move.cord0].sign][0] + s
    if board[move.cord0].sign == PAWN and move.cord1.y in (0,7):
        return s + "=" + reprSign[move.promotion]
    return s
    
def toAN (board, move):
    """ Returns a Algebraic Notation string of a move
        board should be prior to the move """
    
    s = str(move.cord0) + str(move.cord1)
    if board[move.cord0].sign == PAWN and move.cord1.y in (0,7):
        return s + reprSign[move.promotion]
    return s

def toFAN (board, board2, move):
    """ Returns a Figurine Algebraic Notation string of a move """
    return toSAN(board, board2, move, fan=True)

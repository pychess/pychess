import sys
from Utils.Piece import Piece
from Utils.Cord import Cord
from System.Log import log
from copy import copy

def clone2dArray (array):
    l = []
    for row in array:
        l.append([])
        for v in row:
            l[-1].append(v)
    return l

class Board:
    def __init__ (self, array):
        self.data = array
    
    def move (self, move):
        board = Board(clone2dArray(self.data))
        cord0, cord1 = move.cords
        board[cord1] = board[cord0]
        board[cord0] = None
        if move.enpassant:
            board[move.enpassant] = None
        if move.castling:
            board[move.castling[1]] = board[move.castling[0]]
            board[move.castling[0]] = None
        if not board[cord1]: log.warn("How is this move possible? "+str(move))
        if board[cord1] and board[cord1].sign == "p" and cord1.y in [0,7]:
            board[cord1] = Piece(board[cord1].color, move.promotion)
        return board
    
    def __getitem__(self, cord):
        #if type(cord) == int:
        #    return self.data[cord]
        return self.data[cord.y][cord.x]
    
    def __setitem__(self, cord, piece):
        self.data[cord.y][cord.x] = piece
        
    def __delitem__(self, cord):
        self[cord] = None
        
    def __repr__ (self):
        return repr(self.data)

    def __len__ (self):
        return len(self.data)

    def __repr__ (self):
        b = ""
        for r in range(8)[::-1]:
            row = self.data[r]
            for piece in row:
                if piece:
                    sign = piece.sign
                    sign = piece.color == "white" and sign.upper() or sign.lower()
                    b += sign
                else: b += "."
                b += " "
            b += "\n"
        return b
    
    def __eq__ (self, other):
        if type(self) != type(other) or self.__class__ != other.__class__:
            return False
        for y, row in enumerate(self.data):
            for x, piece in enumerate(row):
                oPiece = other.data[y][x]
                if not piece and oPiece: return False
                if not piece and not oPiece: continue
                if not piece.__eq__(oPiece):
                    return False
        return True

    def clone (self):
        l = []
        for row in self.data:
            l.append([])
            for piece in row:
                l[-1].append(piece)
        return Board(l)

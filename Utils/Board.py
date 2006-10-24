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

# In a future release the zobrit table might be used with extra castling etc. flags
# This would be done to move parts like that from history into Board, and thereby reduce history.clone calls.

# Somepeople find 64bit better
zobritMax = 2**31-1
from random import randint
zobrit = []
for sign in ("k","q","r","b","n","p"):
    zobrit.append([])
    for color in ("white", "black"):
        zobrit[-1].append([])
        for x in range(8):
            zobrit[-1][-1].append([])
            for y in range(8):
                zobrit[-1][-1][-1].append(randint(0,zobritMax))

sign2int = {"k":0,"q":1,"r":2,"b":3,"n":4,"p":5}
color2int = {"white":0,"black":1}

class Board:
    
    def __init__ (self, array):
        self.data = array
        self.myhash = 0
        for y, row in enumerate(self.data):
            for x, piece in enumerate(row):
                if not piece: continue
                self.myhash ^= zobrit[sign2int[piece.sign]][color2int[piece.color]][x][y]
    
    def move (self, move):
        board = self.clone()
        cord0, cord1 = move.cords
        
        p = board[cord0]
        board.myhash = self.myhash ^ zobrit[sign2int[p.sign]][color2int[p.color]][cord0.x][cord0.y]
        board.myhash = self.myhash ^ zobrit[sign2int[p.sign]][color2int[p.color]][cord1.x][cord1.y]
        
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
        return hash(self) == hash(other)
        #for y, row in enumerate(self.data):
        #    for x, piece in enumerate(row):
        #        oPiece = other.data[y][x]
        #        if not piece and oPiece: return False
        #        if not piece and not oPiece: continue
        #        if not piece.__eq__(oPiece):
        #            return False
        #return True

    def clone (self):
        l = [[[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]]]
        for y, row in enumerate(self.data):
            for x, piece in enumerate(row):
                l[y][x] = piece
        b = Board(l)
        b.myhash = self.myhash
        return b
    
    def __hash__ (self):
        return self.myhash

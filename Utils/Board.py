import sys
from Utils.Piece import Piece
from Utils.Cord import Cord
from System.Log import log
from Utils.const import *
from Utils import validator

# Somepeople find 64bit better, but python hash only supports int
zobritMax = 2**31-1
from random import randint
zobrit = []
for piece in (WHITE, BLACK):
    zobrit.append([])
    for color in (KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN):
        zobrit[-1].append([])
        for x in range(8):
            zobrit[-1][-1].append([])
            for y in range(8):
                zobrit[-1][-1][-1].append(randint(0,zobritMax))

def rm (var, opp):
    if var & opp:
        return var ^ opp
    return var

a1 = Cord('a1'); d1 = Cord('d1')
h1 = Cord('h1'); f1 = Cord('f1')
a8 = Cord('a8'); d8 = Cord('d8')
h8 = Cord('h8'); f8 = Cord('f8')

class Board:
    def __init__ (self, array):
        self.data = array
        self.enpassant = None
        self.movelist = None
        self.color = WHITE
        self.castling = WHITE_OO | WHITE_OOO | BLACK_OO | BLACK_OOO
        self.status = RUNNING
        self.fifty = 0
        self.myhash = 0
        for y, row in enumerate(self.data):
            for x, piece in enumerate(row):
                if not piece: continue
                try:
                    self.myhash ^= zobrit[piece.color][piece.sign][x][y]
                except: print [piece.color,piece.sign,x,y]
    
    def _move (self, cord0, cord1):
    	p = self[cord0]
    	if not p:
    		print cord0, cord1, self
    	self.myhash = self.myhash ^ zobrit[p.color][p.sign][cord0.x][cord0.y]
        self.myhash = self.myhash ^ zobrit[p.color][p.sign][cord1.x][cord1.y]
    	self[cord1] = p
        self[cord0] = None
    
    def move (self, move, mvlist=False):

        board = self.clone()
        board.movelist = None
        cord0, cord1 = move.cords
        
        p = board[cord0]
        
        if not p:
            print board, cord0
        
        if p.sign == KING:
            if cord0.y == 0:
                if cord0.x - cord1.x == 2:
                    board._move(a1, d1)
                elif cord0.x - cord1.x == -2:
                    board._move(h1, f1)
            else:
                if cord0.x - cord1.x == 2:
                    board._move(a8, d8)
                elif cord0.x - cord1.x == -2:
                    board._move(h8, f8)
        
        elif p.sign == PAWN and cord0.y in (3,4):
            if cord0.x != cord1.x and board[cord1] == None:
                q = board.data[cord0.y][cord1.x]
                if q:
                    board.myhash = board.myhash ^ zobrit[q.color][q.sign][cord1.x][cord0.y]
                    board.data[cord0.y][cord1.x] = None
        
        elif p.sign == PAWN and cord1.y in (0,7):
            q = board[cord0]
            board.myhash = board.myhash ^ zobrit[q.color][q.sign][cord0.x][cord0.y]
            board[cord0] = Piece(q.color, move.promotion)
            q = board[cord0]
            board.myhash = board.myhash ^ zobrit[q.color][q.sign][cord0.x][cord0.y]
            
        board._move(cord0, cord1)
        board.color = 1 - self.color
        
        if board[cord1].sign == KING:
            if abs(cord0.x - cord1.x) == 2:
                if board[cord1].color == WHITE:
                    board.castling |= WHITE_CASTLED
                    board.castling = rm(board.castling, WHITE_OO)
                    board.castling = rm(board.castling, WHITE_OOO)
                else:
                    board.castling |= BLACK_CASTLED
                    board.castling = rm(board.castling, BLACK_OO)
                    board.castling = rm(board.castling, BLACK_OOO)
            else:
                if board[cord1].color == WHITE:
                    board.castling = rm(board.castling, WHITE_OO)
                    board.castling = rm(board.castling, WHITE_OOO)
                else:
                    board.castling = rm(board.castling, BLACK_OO)
                    board.castling = rm(board.castling, BLACK_OOO)
        
        elif board[cord1].sign == ROOK:
            if board[cord1].color == WHITE:
                if cord0 == a1: board.castling =   rm(board.castling, WHITE_OOO)
                elif cord0 == h1: board.castling = rm(board.castling, WHITE_OO)
            else:
                if cord0 == a8: board.castling = rm(board.castling, BLACK_OOO)
                elif cord0 == h8: board.castling = rm(board.castling, BLACK_OO)
        
        elif board[cord1].sign == PAWN and abs(cord0.y - cord1.y) == 2:
            board.enpassant = Cord(cord0.x, (cord0.y+cord1.y)/2)
        
        else: board.enpassant = None
        
        iscapture = self[cord1] != None
        if iscapture or board[cord1].sign != PAWN:
            board.fifty += 1
        else: board.fifty = 0
        
        if mvlist:
            board.movelist = validator.findMoves(board)
        
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
                    sign = reprSign[piece.sign][0]
                    sign = piece.color == WHITE and sign.upper() or sign.lower()
                    b += sign
                else: b += "."
                b += " "
            b += "\n"
        return b
    
    def __eq__ (self, other):
        if not isinstance(other, Board) or \
                self.castling != other.castling:
            return False
        #TODO: Test flags
        for y, row in enumerate(self.data):
            for x, piece in enumerate(row):
                oPiece = other.data[y][x]
                if not piece and oPiece: return False
                if not piece and not oPiece: continue
                if not piece.__eq__(oPiece):
                    return False
        return True

    def clone (self):
        l = [[[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]]]
        for y, row in enumerate(self.data):
            for x, piece in enumerate(row):
                l[y][x] = piece
        b = Board(l)
        b.myhash = self.myhash
        b.enpassant = self.enpassant
        b.movelist = self.movelist
        b.color = self.color
        b.castling = self.castling
        b.status = self.status
        b.fifty = self.fifty
        return b
    
    def __hash__ (self):
        return self.myhash

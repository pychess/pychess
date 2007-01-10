import sys
from pychess.Utils.Piece import Piece
from pychess.Utils.Cord import Cord
from pychess.System.Log import log
from pychess.System.MultiArray import MultiArray
from pychess.Utils.const import *
from pychess.Utils import validator

# We use 64 bit for comparing, but only 32 for __hash__
#zobritMax = 2**64
zobritMax = sys.maxint
from random import randint
zobritOnline = []
for color in range(2):
    for piece in range(8):
        for x in range(8):
            for y in range(8):
                n = randint(0,zobritMax)
                zobritOnline.append(n)
zobrit = MultiArray('I',8,zobritOnline)

def rm (var, opp):
    if var & opp:
        return var ^ opp
    return var

a1 = Cord('a1'); d1 = Cord('d1')
h1 = Cord('h1'); f1 = Cord('f1')
a8 = Cord('a8'); d8 = Cord('d8')
h8 = Cord('h8'); f8 = Cord('f8')

class MoveError (Exception): pass

class Board:
    def __init__ (self, array, ar_hash=-1):
        self.data = array
        self.enpassant = None
        self.movelist = None
        self.color = WHITE
        self.castling = WHITE_OO | WHITE_OOO | BLACK_OO | BLACK_OOO
        self.status = RUNNING
        self.fifty = 0
        self.myhash = 0
        if ar_hash == -1:
            for y, row in enumerate(self.data):
                for x, piece in enumerate(row):
                    if not piece: continue
                    self.myhash ^= zobrit.get(piece.color,piece.sign,x,y)
        else: self.myhash = ar_hash
    
    def _move (self, cord0, cord1):
    	p = self[cord0]
    	self.myhash = self.myhash ^ zobrit.get(p.color,p.sign,cord0.x,cord0.y)
        self.myhash = self.myhash ^ zobrit.get(p.color,p.sign,cord1.x,cord1.y)
    	self[cord1] = p
        self[cord0] = None
    
    def move (self, move, mvlist=False):

        board = self.clone()
        board.movelist = None
        cord0, cord1 = move.cords
        
        if self[cord1] and self[cord1].sign == KING:
            raise MoveError, "Trying to capture king in %s %s %s\n%s" % \
                    (str(move), cord1, self[cord1], str(self))
        
        p = board[cord0]
        
        if not p:
            raise MoveError, "%s%s %s" % (board, move, cord0)
        
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
                    board.myhash = board.myhash ^ zobrit.get(q.color,q.sign,cord1.x,cord0.y)
                    board.data[cord0.y][cord1.x] = None
        
        elif p.sign == PAWN and cord1.y in (0,7):
            q = board[cord0]
            board.myhash = board.myhash ^ zobrit.get(q.color,q.sign,cord0.x,cord0.y)
            board[cord0] = Piece(q.color, move.promotion)
            q = board[cord0]
            board.myhash = board.myhash ^ zobrit.get(q.color,q.sign,cord0.x,cord0.y)
        
        if cord1 == a8:
            board.castling = rm(board.castling, BLACK_OOO)
        elif cord1 == h8:
            board.castling = rm(board.castling, BLACK_OO)
        elif cord1 == a1:
            board.castling = rm(board.castling, WHITE_OOO)
        elif cord1 == h1:
            board.castling = rm(board.castling, WHITE_OO)
            
        ########################################################################
        # The move is here                                                     #
        ########################################################################
        
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
        
        if board[cord1].sign == PAWN and abs(cord0.y - cord1.y) == 2:
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
        b = reprColor[self.color]+"\n"
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
    
    def __cmp__ (self, other):
        if other == None:
            return 1
        if cmp (self.myhash, other.myhash):
            return cmp (self.myhash, other.myhash)
        if cmp (self.castling, other.castling):
            return cmp (self.castling, other.castling)
        if cmp (self.enpassant, other.enpassant):
            return cmp (self.enpassant, other.enpassant)
        return cmp (self.color, other.color)
    
    def __eq__ (self, other):
        return  other != None and \
                self.myhash == other.myhash and \
                self.castling == other.castling and \
                self.enpassant == other.enpassant and \
                self.color == other.color
        
    def clone (self):
        l = [[[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]], [[None], [None], [None], [None], [None], [None], [None], [None]]]
        for y, row in enumerate(self.data):
            for x, piece in enumerate(row):
                l[y][x] = piece
        b = Board(l, self.myhash)
        b.enpassant = self.enpassant
        b.movelist = self.movelist
        b.color = self.color
        b.castling = self.castling
        b.status = self.status
        b.fifty = self.fifty
        return b
    
    def __hash__ (self):
        v = int(self.myhash)
        if v > sys.maxint:
            v  = v >> 1
        return v -1 + self.color

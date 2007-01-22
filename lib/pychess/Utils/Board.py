import sys
from lutils.LBoard import LBoard
from Piece import Piece
from Cord import Cord
from const import *

class Board (LBoard):
    """ Board is a thin layer above LBoard, adding the Piece objects, which are
        needed for animation in BoardView.
        In contrast to LBoard, Board is immutable, which means it will clone
        itself each time you apply a move to it. """
    
    def __init__ (self):
        self.data = [[None]*8 for i in xrange(8)]
    
    def applyFen (self, fenstr):
        newBoard = self.clone()
        LBoard.applyFen (newBoard, fenstr)
        
        arBoard = self.arBoard
        wpieces = self.boards[WHITE]
        for cord in iterBits(wpieces[PAWN]):
            self.data[RANK(cord)][FILE(cord)] = Piece(WHITE, PAWN)
        for cord in iterBits(wpieces[KNIGHT]):
            self.data[RANK(cord)][FILE(cord)] = Piece(WHITE, KNIGHT)
        for cord in iterBits(wpieces[BISHOP]):
            self.data[RANK(cord)][FILE(cord)] = Piece(WHITE, BISHOP)
        for cord in iterBits(wpieces[ROOK]):
            self.data[RANK(cord)][FILE(cord)] = Piece(WHITE, ROOK)
        for cord in iterBits(wpieces[QUEEN]):
            self.data[RANK(cord)][FILE(cord)] = Piece(WHITE, QUEEN)
        
        bpieces = board.boards[BLACK]
        for cord in iterBits(bpieces[PAWN]):
            self.data[RANK(cord)][FILE(cord)] = Piece(BLACK, PAWN)
        for cord in iterBits(bpieces[KNIGHT]):
            self.data[RANK(cord)][FILE(cord)] = Piece(BLACK, KNIGHT)
        for cord in iterBits(bpieces[BISHOP]):
            self.data[RANK(cord)][FILE(cord)] = Piece(BLACK, BISHOP)
        for cord in iterBits(bpieces[ROOK]):
            self.data[RANK(cord)][FILE(cord)] = Piece(BLACK, ROOK)
        for cord in iterBits(bpieces[QUEEN]):
            self.data[RANK(cord)][FILE(cord)] = Piece(BLACK, QUEEN)
            
        return newBoard
    
    def _addPiece (self, cord, piece, color):
        self[Cord(cord)] = Piece(color, piece)
        LBoard._addPiece (self, cord, piece, color)
    
    def _removePiece (self, cord, piece, color):
        self[Cord(cord)] = None
        LBoard._removePiece (self, cord, piece, color)
    
    def _move (self, fcord, tcord, piece, color):
        self[Cord(tcord)] = self[Cord(fcord)]
        self[Cord(fcord)] = None
        LBoard._move (self, fcord, tcord, piece, color)
    
    def move (self, move, mvlist=False):
        newBoard = self.clone()
        LBoard.applyMove (newBoard, move.move)
        return newBoard
    
    def __getitem__ (self, cord):
        return self.data[cord.y][cord.x]
    
    def __setitem__ (self, cord, piece):
        self.data[cord.y][cord.x] = piece
    
    def __delitem__ (self, cord):
        self[cord] = None
	
    def __len__ (self):
        return 8
    
    def clone (self):
        newBoard = Board()
        fenstr = self.asFen()
        LBoard.applyFen (newboard, fenstr)
        return newBoard

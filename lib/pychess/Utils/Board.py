import sys
from lutils.LBoard import LBoard
from lutils.LBoard import FEN_START
from Piece import Piece
from Cord import Cord
from const import *

from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, GObject

class Board (LBoard, GObject):
    """ Board is a thin layer above LBoard, adding the Piece objects, which are
        needed for animation in BoardView.
        In contrast to LBoard, Board is immutable, which means it will clone
        itself each time you apply a move to it. """
    
    __gsignals__ = {
        "changed": (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        "game_ended": (SIGNAL_RUN_FIRST, TYPE_NONE, (int, int))
    }
    
    def __init__ (self):
        self.data = [[None]*8 for i in xrange(8)]
        self.applyFen (FEN_START)
    
    def fromFen (self, fenstr):
        newBoard = Board()
        LBoard.applyFen (newBoard, fenstr)
        
        arBoard = newBoard.arBoard
        wpieces = newBoard.boards[WHITE]
        for cord in iterBits(wpieces[PAWN]):
            newBoard.data[RANK(cord)][FILE(cord)] = Piece(WHITE, PAWN)
        for cord in iterBits(wpieces[KNIGHT]):
            newBoard.data[RANK(cord)][FILE(cord)] = Piece(WHITE, KNIGHT)
        for cord in iterBits(wpieces[BISHOP]):
            newBoard.data[RANK(cord)][FILE(cord)] = Piece(WHITE, BISHOP)
        for cord in iterBits(wpieces[ROOK]):
            newBoard.data[RANK(cord)][FILE(cord)] = Piece(WHITE, ROOK)
        for cord in iterBits(wpieces[QUEEN]):
            newBoard.data[RANK(cord)][FILE(cord)] = Piece(WHITE, QUEEN)
        
        bpieces = board.boards[BLACK]
        for cord in iterBits(bpieces[PAWN]):
            newBoard.data[RANK(cord)][FILE(cord)] = Piece(BLACK, PAWN)
        for cord in iterBits(bpieces[KNIGHT]):
            newBoard.data[RANK(cord)][FILE(cord)] = Piece(BLACK, KNIGHT)
        for cord in iterBits(bpieces[BISHOP]):
            newBoard.data[RANK(cord)][FILE(cord)] = Piece(BLACK, BISHOP)
        for cord in iterBits(bpieces[ROOK]):
            newBoard.data[RANK(cord)][FILE(cord)] = Piece(BLACK, ROOK)
        for cord in iterBits(bpieces[QUEEN]):
            newBoard.data[RANK(cord)][FILE(cord)] = Piece(BLACK, QUEEN)
        
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
    
    def willLeaveInCheck (self, move):
        LBoard.applyMove (self, move.move)
        result = self.opIsChecked()
        LBoard.popMove (self)
        return result
    
    def switchColor (self):
        """ Switches the current color to move and unsets the enpassant cord.
            Mostly to be used by inversed analyzers """
        newBoard = self.clone()
        newBoard.setColor(1-newBoard.color)
        newBoard.setEnpassant(None)
        return newBoard
    
    def _get_epcord (self):
        if self.enpassant != None:
            return Cord(self.enpassant)
        return None
    epcord = property(_get_epcord)
    
    def __getitem__ (self, cord):
        return self.data[cord.y][cord.x]
    
    def __setitem__ (self, cord, piece):
        self.data[cord.y][cord.x] = piece
    
    def __delitem__ (self, cord):
        self[cord] = None
	
    def __len__ (self):
        return 8
    
    def clone (self):
        fenstr = self.asFen()
        newBoard = Board()
        LBoard.applyFen (newBoard, fenstr)
        return newBoard

from copy import copy

from lutils.LBoard import LBoard
from lutils.bitboard import iterBits
from lutils.lmove import RANK, FILE, FLAG, PROMOTE_PIECE, toAN
from Piece import Piece
from Cord import Cord
from const import *


class Board:
    """ Board is a thin layer above LBoard, adding the Piece objects, which are
        needed for animation in BoardView.
        In contrast to LBoard, Board is immutable, which means it will clone
        itself each time you apply a move to it.
        Caveat: As the only objects, the Piece objects in the self.data lists
        will not be cloned, to make animation state preserve between moves """
    
    variant = NORMALCHESS
    
    def __init__ (self, setup=False):
        self.data = [[None]*8 for i in xrange(8)]
        self.board = LBoard(self)
        
        if setup:
            if setup == True:
                self.board.applyFen(FEN_START)
            else: self.board.applyFen(setup)
            
            arBoard = self.board.arBoard
            wpieces = self.board.boards[WHITE]
            bpieces = self.board.boards[BLACK]
            
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
            if self.board.kings[WHITE] != -1:
                self[Cord(self.board.kings[WHITE])] = Piece(WHITE, KING)
            
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
            if self.board.kings[BLACK] != -1:
                self[Cord(self.board.kings[BLACK])] = Piece(BLACK, KING)

    def move (self, move):
        
        assert self[move.cord0], "%s %s" % (move, self.asFen())
        
        newBoard = self.clone()
        newBoard.board.applyMove (move.move)
        
        cord0, cord1 = move.cords
        flag = FLAG(move.move)
        
        newBoard[cord1] = newBoard[cord0]
        newBoard[cord0] = None
        
        if self.color == WHITE:
            if flag == QUEEN_CASTLE:
                newBoard[Cord(D1)] = newBoard[Cord(A1)]
                newBoard[Cord(A1)] = None
            elif flag == KING_CASTLE:
                newBoard[Cord(F1)] = newBoard[Cord(H1)]
                newBoard[Cord(H1)] = None
        else:
            if flag == QUEEN_CASTLE:
                newBoard[Cord(D8)] = newBoard[Cord(A8)]
                newBoard[Cord(A8)] = None
            elif flag == KING_CASTLE:
                newBoard[Cord(F8)] = newBoard[Cord(H8)]
                newBoard[Cord(H8)] = None

        if flag in PROMOTIONS:
            newBoard[cord1] = Piece(self.color, PROMOTE_PIECE(flag))
        
        elif flag == ENPASSANT:
            newBoard[Cord(cord1.x, cord0.y)] = None
        
        return newBoard

    def willLeaveInCheck (self, move):
        self.board.lock.acquire()
        try:
            self.board.applyMove(move.move)
            result = self.board.opIsChecked()
            self.board.popMove()
        finally:
            self.board.lock.release()
        return result
    
    def switchColor (self):
        """ Switches the current color to move and unsets the enpassant cord.
            Mostly to be used by inversed analyzers """
        return self.setColor(1-self.color)
    
    def _get_enpassant (self):
        if self.board.enpassant != None:
            return Cord(self.board.enpassant)
        return None
    enpassant = property(_get_enpassant)
    
    def setColor (self, color):
        newBoard = self.clone()
        newBoard.board.setColor(color)
        newBoard.board.setEnpassant(None)
        return newBoard
    
    def _get_color (self):
        return self.board.color
    color = property(_get_color)
    
    def _get_ply (self):
        return len(self.board.history)
    ply = property(_get_ply)
    
    def asFen (self):
        return self.board.asFen()
    
    def __repr__ (self):
        return str(self.board)
    
    def __getitem__ (self, cord):
        return self.data[cord.y][cord.x]
    
    def __setitem__ (self, cord, piece):
        self.data[cord.y][cord.x] = piece
    
    def clone (self):
        fenstr = self.asFen()
        
        lboard = LBoard(self)
        lboard.applyFen (fenstr)
        lboard.history = copy(self.board.history)
        lboard.ini_kings = copy(self.board.ini_kings)
        lboard.ini_rooks = copy(self.board.ini_rooks)
        
        if self.variant == FISCHERRANDOMCHESS:
            from pychess.Variants.fischerandom import FRCBoard
            newBoard = FRCBoard()
        else:
            newBoard = Board()
        newBoard.board = lboard

        for y, row in enumerate(self.data):
            for x, piece in enumerate(row):
                newBoard.data[y][x] = piece
        
        return newBoard

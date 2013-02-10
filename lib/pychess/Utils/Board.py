from copy import copy

from lutils.LBoard import LBoard
from lutils.bitboard import iterBits
from lutils.lmove import RANK, FILE, FCORD, FLAG, PROMOTE_PIECE, toAN
from Piece import Piece
from Cord import Cord
from const import *

RANKS = 8
FILES = 8

def reverse_enum(L):
    for index in reversed(xrange(len(L))):
        yield index, L[index]


class Board:
    """ Board is a thin layer above LBoard, adding the Piece objects, which are
        needed for animation in BoardView.
        In contrast to LBoard, Board is immutable, which means it will clone
        itself each time you apply a move to it.
        Caveat: As the only objects, the Piece objects in the self.data lists
        will not be cloned, to make animation state preserve between moves """
    
    variant = NORMALCHESS
    
    def __init__ (self, setup=False, lboard=None):
        self.data = [dict(enumerate([None]*FILES)) for i in xrange(RANKS)]
        if lboard is None:
            self.board = LBoard(self.variant)
        else:
            self.board = lboard
        self.board.pieceBoard = self
        
        if setup:
            if lboard is None:
                if setup == True:
                    self.board.applyFen(FEN_START)
                elif isinstance(setup, basestring):
                    self.board.applyFen(setup)
            
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
            
    def getHoldingCord(self, color, piece):
        enum = reverse_enum if color == WHITE else enumerate
        x1 = -1 if color==BLACK else FILES
        x2 = -2 if color==BLACK else FILES+1
        for i, row in enum(self.data):
            for x in (x2, x1):
                if row.get(x) is not None:
                    if row.get(x).piece == piece:
                        return Cord(x, i)

    def newHoldingCord(self, color, piece):
        enum = reverse_enum if color == BLACK else enumerate
        x1 = -1 if color == BLACK else FILES
        x2 = -2 if color == BLACK else FILES+1
        for i, row in enum(self.data):
            for x in (x1, x2):
                if row.get(x) is None:
                    return Cord(x, i)
        
    def simulateMove (self, board1, move, show_captured=False):
        moved = []
        new = []
        dead = []
        
        if move.flag == NULL_MOVE:
            return moved, new, dead
            
        cord0, cord1 = move.cords
        
        if move.flag == DROP:
            piece = FCORD(move.move)
            cord0 = self.getHoldingCord(self.color, piece)
            moved.append( (self[cord0], cord0) )
            return moved, new, dead
            
        moved.append( (self[cord0], cord0) )

        if self[cord1]:
            if self.variant == CRAZYHOUSECHESS or show_captured:
                piece = PAWN if self.variant == CRAZYHOUSECHESS and self[cord1].promoted else self[cord1].piece
                cord = self.newHoldingCord(self.color, piece)
                moved.append( (board1[cord], cord1) )
                new.append( board1[cord] )
            else:
                dead.append( self[cord1] )
        
        if move.flag == QUEEN_CASTLE:
            if self.color == WHITE:
                moved.append( (self[Cord(A1)], Cord(A1)) )
            else:
                moved.append( (self[Cord(A8)], Cord(A8)) )
        elif move.flag == KING_CASTLE:
            if self.color == WHITE:
                moved.append( (self[Cord(H1)], Cord(H1)) )
            else:
                moved.append( (self[Cord(H8)], Cord(H8)) )
        
        elif move.flag in PROMOTIONS:
            newPiece = board1[cord1]
            moved.append( (newPiece, cord0) )
            new.append( newPiece )
        
        elif move.flag == ENPASSANT:
            shift = -1 if self.color == WHITE else 1
            ep_cord = Cord(cord1.x, cord1.y + shift)
            if self.variant == CRAZYHOUSECHESS or show_captured:
                moved.append( (self[ep_cord], ep_cord) )
                cord = self.newHoldingCord(self.color, PAWN)
                new.append( board1[cord] )
            else:
                dead.append( self[ep_cord] )
        
        return moved, new, dead
    
    def simulateUnmove (self, board1, move, show_captured=False):
        moved = []
        new = []
        dead = []
        
        if move.flag == NULL_MOVE:
            return moved, new, dead
        
        cord0, cord1 = move.cords
        
        moved.append( (self[cord1], cord1) )
        
        if board1[cord1]:
            if self.variant == CRAZYHOUSECHESS or show_captured:
                piece = PAWN if self.variant == CRAZYHOUSECHESS and board1[cord1].promoted else board1[cord1].piece
                cord = self.getHoldingCord(1-self.color, piece)
                moved.append( (self[cord], cord) )
                self[cord].opacity = 1
                dead.append( self[cord] )
            else:
                dead.append( board1[cord1] )
        
        if move.flag == QUEEN_CASTLE:
            if board1.color == WHITE:
                moved.append( (self[Cord(D1)], Cord(D1)) )
            else:
                moved.append( (self[Cord(D8)], Cord(D8)) )
        elif move.flag == KING_CASTLE:
            if board1.color == WHITE:
                moved.append( (self[Cord(F1)], Cord(F1)) )
            else:
                moved.append( (self[Cord(F8)], Cord(F8)) )
        
        elif move.flag in PROMOTIONS:
            newPiece = board1[cord0]
            moved.append( (newPiece, cord1) )
            new.append( newPiece )
        
        elif move.flag == ENPASSANT:
            if self.variant == CRAZYHOUSECHESS or show_captured:
                cord = self.getHoldingCord(1-self.color, PAWN)
                moved.append( (self[cord], cord) )
                self[cord].opacity = 1
                dead.append( self[cord] )
            else:
                if board1.color == WHITE:
                    new.append( board1[Cord(cord1.x, cord1.y-1)] )
                else:
                    new.append( board1[Cord(cord1.x, cord1.y+1)] )
        
        return moved, new, dead
    
    def move (self, move, lboard=None, show_captured=False):
        """ Creates a new Board object cloning itself then applying
            the move.move to the clone Board's lboard.
            If lboard param was given, it will be used when cloning,
            and move will not be applyed, just the high level Piece
            objects will be adjusted.""" 
        flag = FLAG(move.move)
        if flag != DROP:
            assert self[move.cord0], "%s %s" % (move, self.asFen())
        
        newBoard = self.clone(lboard=lboard)
        if lboard is None:
            newBoard.board.applyMove (move.move)

        cord0, cord1 = move.cords

        if self[move.cord1] is not None or flag == ENPASSANT:
            if self.variant == CRAZYHOUSECHESS or show_captured:
                if self.variant == CRAZYHOUSECHESS:
                    piece = PAWN if flag == ENPASSANT or self[move.cord1].promoted else self[move.cord1].piece
                    new_piece = Piece(self.color, piece)
                else:
                    piece = PAWN if flag == ENPASSANT else self[move.cord1].piece
                    new_piece = Piece(1-self.color, piece)
                newBoard[self.newHoldingCord(self.color, piece)] = new_piece
        
        if flag == DROP:
            piece = FCORD(move.move)
            newBoard[cord1] = newBoard[self.getHoldingCord(self.color, piece)]
            newBoard[self.getHoldingCord(self.color, piece)] = None
        else:
            newBoard[cord1] = newBoard[cord0]
            
        if flag != NULL_MOVE and flag != DROP:
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
            new_piece = Piece(self.color, PROMOTE_PIECE(flag))
            new_piece.promoted = True
            newBoard[cord1] = new_piece
        
        elif flag == ENPASSANT:
            newBoard[Cord(cord1.x, cord0.y)] = None
        
        return newBoard
    
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
        return self.board.plyCount
    ply = property(_get_ply)
    
    def asFen (self):
        return self.board.asFen()
    
    def __repr__ (self):
        return str(self.board)
    
    def __getitem__ (self, cord):
        return self.data[cord.y].get(cord.x)
     
    def __setitem__ (self, cord, piece):
        self.data[cord.y][cord.x] = piece
    
    def clone (self, lboard=None):
        if lboard is None:
            lboard = self.board.clone()
        
        if self.variant != NORMALCHESS:
            from pychess.Variants import variants
            newBoard = variants[self.variant].board()
        else:
            newBoard = Board()
        newBoard.board = lboard
        newBoard.board.pieceBoard = newBoard
        
        for y, row in enumerate(self.data):
            for x, piece in row.items():
                newBoard.data[y][x] = piece
        
        return newBoard
    
    def __eq__ (self, other):
        if type(self) != type(other): return False
        return self.board == other.board

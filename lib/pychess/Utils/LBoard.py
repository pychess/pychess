
from pychess.Utils.const import *
from bitboard import *

r90 = [
    A8, A7, A6, A5, A4, A3, A2, A1,
    B8, B7, B6, B5, B4, B3, B2, B1,
    C8, C7, C6, C5, C4, C3, C2, C1,
    D8, D7, D6, D5, D4, D3, D2, D1,
    E8, E7, E6, E5, E4, E3, E2, E1,
    F8, F7, F6, F5, F4, F3, F2, F1,
    G8, G7, G6, G5, G4, G3, G2, G1,
    H8, H7, H6, H5, H4, H3, H2, H1
]

r45 = [
    E4, F3, H2, C2, G1, D1, B1, A1,
    E5, F4, G3, A3, D2, H1, E1, C1,
    D6, F5, G4, H3, B3, E2, A2, F1, 
    B7, E6, G5, H4, A4, C3, F2, B2,
    G7, C7, F6, H5, A5, B4, D3, G2, 
    C8, H7, D7, G6, A6, B5, C4, E3, 
    F8, D8, A8, E7, H6, B6, C5, D4, 
    H8, G8, E8, B8, F7, A7, C6, D5
]

r315 = [
    A1, C1, F1, B2, G2, E3, D4, D5,
    B1, E1, A2, F2, D3, C4, C5, C6,
    D1, H1, E2, C3, B4, B5, B6, A7,
    G1, D2, B3, A4, A5, A6, H6, F7,
    C2, A3, H3, H4, H5, G6, E7, B8,
    H2, G3, G4, G5, F6, D7, A8, E8,
    F3, F4, F5, E6, C7, H7, D8, G8,
    E4, E5, D6, B7, G7, C8, F8, H8
]

################################################################################
# Zobrit hashing 32 bit implementation                                         #
################################################################################

from sys import maxint
from random import randint

pieceHashes = [[[0]*64 for i in range(7)] for j in range(2)]
for color in WHITE, BLACK:
    for piece in PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING:
        for cord in range(64):
            pieceHashes[color][piece][cord] = randint(0, maxint)

epHashes = []
for cord in range(64):
    epHashes.append(randint(0, maxint))

W_OOHash = randint(0, maxint)
W_OOOHash = randint(0, maxint)
B_OOHash = randint(0, maxint)
B_OOOHash = randint(0, maxint)

# Will be set each time black is on move
colorHash = randint(0, maxint)

# 50 moves rule is not hashed, as it is so rarly used and would greatly damage
# our transposition table.

################################################################################
# LBoard                                                                       #
################################################################################

from array import array
emptyBoard = array("b", [0]*64).tostring()

# hash(array.tostring()) tager 1.5e-06 sekunder. Så måske er den forlangsom til
# hash? Måske kan den bruges til at slå op i book?

class LBoard:
    def __init__ (self):
        self.blocker45 = 0
        self.blocker315 = 0
        self.blocker = 0
        self.blocker90 = 0
        
        self.friends = [0]*2
        self.kings = [-1]*2
        self.boards = [[0]*7 for i in range(2)]
        
        self.enpassant = -1
        self.color = WHITE
        self.castling = B_OOO | B_OO | W_OOO | W_OO
        self.fifty = 0
        
        self.arBoard = array("b")
        self.arBoard.fromstring(emptyBoard)
        
        self.hash = 0
        self.pawnhash = 0
        
        self.history = []
    
    def setUpPosition (self):
        self._addPiece(E4, ROOK, WHITE)
        
        self._addPiece(A1, ROOK, WHITE)
        self._addPiece(B1, KNIGHT, WHITE)
        self._addPiece(C1, BISHOP, WHITE)
        self._addPiece(D1, KING, WHITE)
        self._addPiece(E1, QUEEN, WHITE)
        self._addPiece(F1, BISHOP, WHITE)
        self._addPiece(G1, KNIGHT, WHITE)
        self._addPiece(H1, ROOK, WHITE)
        
        for i in range(A2,H2+1):
            self._addPiece(i, PAWN, WHITE)
            
        for i in range(A7,H7+1):
            self._addPiece(i, PAWN, BLACK)
            
        self._addPiece(A8, ROOK, BLACK)
        self._addPiece(B8, KNIGHT, BLACK)
        self._addPiece(C8, BISHOP, BLACK)
        self._addPiece(D8, QUEEN, BLACK)
        self._addPiece(E8, KING, BLACK)
        self._addPiece(F8, BISHOP, BLACK)
        self._addPiece(G8, KNIGHT, BLACK)
        self._addPiece(H8, ROOK, BLACK)
        
        self.friends[WHITE] = sum(self.boards[WHITE])
        self.friends[BLACK] = sum(self.boards[BLACK])
        self.blocker = self.friends[WHITE] | self.friends[BLACK]
        
    def _addPiece (self, cord, piece, color):
        self.boards[color][piece] = \
                setBit(self.boards[color][piece], cord)
        self.blocker90 = setBit(self.blocker90, r90[cord])
        self.blocker45 = setBit(self.blocker45, r45[cord])
        self.blocker315 = setBit(self.blocker315, r315[cord])
        
        if piece == PAWN:
            self.pawnhash ^= pieceHashes[color][PAWN][cord]
        
        self.hash ^= pieceHashes[color][piece][cord]
        self.arBoard[cord] = piece
    
    def _removePiece (self, cord, piece, color):
        self.boards[color][piece] = \
                clearBit(self.boards[color][piece], cord)
        self.blocker90 = clearBit(self.blocker90, r90[cord])
        self.blocker45 = clearBit(self.blocker45, r45[cord])
        self.blocker315 = clearBit(self.blocker315, r315[cord])
        
        if piece == PAWN:
            self.pawnhash ^= pieceHashes[color][PAWN][cord]
        
        self.hash ^= pieceHashes[color][piece][cord]
        self.arBoard[cord] = EMPTY
    
    def _move (fcord, tcord, piece, color):
        self._removePiece(fcord, piece, color)
        self._addPiece(tcord, piece, color)
    
    def updateBoard (self):
        self.friends[WHITE] = sum(self.boards[WHITE])
        self.friends[BLACK] = sum(self.boards[BLACK])
        self.blocker = self.friends[WHITE] | self.friends[BLACK]
    
    def setColor (self, color):
        if color == self.color: return
        self.color = color
        self.hash ^= colorHash
    
    def applyMove (self, move):
        flag = move >> 12
        fcord = (move >> 6) & 63
        tcord = move & 63
        
        fpiece = self.arBoard[fcord]
        tpiece = self.arBoard[tcord]
        
        opcolor = 1-self.color
        
        # Update history
        self.history.append (
            (move, tpiece, self.enpassant,
            self.castling, self.hash, self.fifty)
        )
        
        if fpiece == PAWN:

            if flag == ENPASSANT:
                takenPawnC = self.enpassant + (self.color == WHITE and -8 or 8)
                self._removePiece (takenPawnC, PAWN, opcolor)
                
            elif flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                          BISHOP_PROMOTION, KNIGHT_PROMOTION):
                piece = flag - 2 # The flags has values: 4, 5, 6, 7
                self._removePiece(fcord, PAWN, self.color)
                self._addPiece(tcord, piece, self.color)
        
        if fpiece == PAWN and abs(fcord-tcord) == 16:
            self.enpassant = (fcord + tcord) / 2
        else: self.enpassant = None
        
        if fpiece == KING:
            self.kings[self.color] = tcord
        
        if flag in (KING_CASTLE, QUEEN_CASTLE):
            if flag == QUEEN_CASTLE:
                rookf = fcord - 4
                rookt = fcord - 1
            else:
                rookf = fcord + 3
                rookt = fcord + 1
            self._move (rookf, rookt, ROOK, self.color)
            if self.color == WHITE:
                self.castling |= W_CASTLED
            else: self.castling |= B_CASTLED
        
        if tpiece == EMPTY and fpiece != PAWN and \
                not flag in (KING_CASTLE, QUEEN_CASTLE):
            self.fifty += 1
        else:
            self.fifty = 0
        
        # Capture
        if tpiece != EMPTY:
            self._removePiece(tcord, tpiece, opcolor)
        
        # Clear castle flags
        if self.color == WHITE:
            if fpiece == KING:
                if self.castling & W_OOO:
                    self.hash ^= W_OOOHash
                    self.castling &= ~W_OOO
                    
                if self.castling & W_OO:
                    self.hash ^= W_OOHash
                    self.castling &= ~W_OO
                    
            if fpiece == ROOK:
                if fcord == H1:
                    if self.castling & W_OO:
                        self.hash ^= W_OOHash
                        self.castling &= ~W_OO
                    
                elif fcord == A1:
                    if self.castling & W_OOO:
                        self.hash ^= W_OOOHash
                        self.castling &= ~W_OOO
            
            if tpiece == ROOK:
                if fcord == H8:
                    if self.castling & B_OO:
                        self.hash ^= B_OOHash
                        self.castling &= ~B_OO
                    
                elif fcord == A8:
                    if self.castling & B_OOO:
                        self.hash ^= B_OOOHash
                        self.castling &= ~B_OOO
        else:
            if fpiece == KING:
                if self.castling & B_OOO:
                    self.hash ^= B_OOOHash
                    self.castling &= ~B_OOO
                    
                if self.castling & B_OO:
                    self.hash ^= B_OOHash
                    self.castling &= ~B_OO
                    
            if fpiece == ROOK:
                if fcord == H8:
                    if self.castling & B_OO:
                        self.hash ^= B_OOHash
                        self.castling &= ~B_OO
                    
                elif fcord == A8:
                    if self.castling & B_OOO:
                        self.hash ^= B_OOOHash
                        self.castling &= ~B_OOO
            
            if tpiece == ROOK:
                if fcord == H1:
                    if self.castling & W_OO:
                        self.hash ^= W_OOHash
                        self.castling &= ~W_OO
                    
                elif fcord == A1:
                    if self.castling & W_OOO:
                        self.hash ^= W_OOOHash
                        self.castling &= ~W_OOO
        
        self._move(fcord, tcord, fpiece, self.color)
        self.setColor(opcolor)
        self.updateBoard ()
        
        return move # Move is returned with the captured piece flag set
    
    def popMove (self):
        
        # Note that we remove the last made move, which was not made by boards
        # current color, but by its opponent
        color = 1 - self.color
        opcolor = self.color
        
        # Get information from history
        move, cpiece, enpassant, castling, hash, fifty = self.history.pop()
        
        flag = move >> 12
        fcord = (move >> 6) & 63
        tcord = move & 63
        
        tpiece = self.arBoard[tcord]
        
        self.removePiece (tcord, tpiece, color)
        
        # Put back captured piece
        if cpiece != EMPTY:
            self._addPiece (tcord, cpiece, opcolor)
       	    self._addPiece (fcord, tpiece, color)
       	
       	# Put back piece captured by enpassant
       	elif flag == ENPASSANT:
            epcord = color == WHITE and tcord - 8 or tcord + 8
            self._addPiece (epcord, PAWN, opcolor)
            self._addPiece (fcord, PAWN, color)
            
       	# Put back promoted pawn
       	elif flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                    BISHOP_PROMOTION, KNIGHT_PROMOTION):
            self._addPiece (fcord, PAWN, color)
        
        # Put back moved piece
        else:
            self._addPiece (fcord, tpiece, color)
        
        # Pyt back rook moved by castling
        if flag in (KING_CASTLE, QUEEN_CASTLE):
            if flag == QUEEN_CASTLE:
                rookf = fcord - 4
                rookt = fcord - 1
            else:
                rookf = fcord + 3
                rookt = fcord + 1
            self._move (rookt, rookf, ROOK, self.color)
        
        self.enpassant = enpassant
        self.castling = castling
        self.hash = hash
        self.fifty = fifty
        
    def __hash__ (self):
        return self.hash

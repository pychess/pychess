
from array import array

from pychess.Utils.const import *
from ldata import *
from attack import isAttacked
from bitboard import *

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
# FEN                                                                          #
################################################################################

# This will cause applyFen to raise an exception, if halfmove clock and fullmove
# number is not specified
STRICT_FEN = True

# A few nice to have boards
FEN_EMPTY = "8/8/8/8/8/8/8/8 w KQkq - 0 1"
FEN_START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

################################################################################
# LBoard                                                                       #
################################################################################

class LBoard:
    def __init__ (self):
        self._reset()
    
    def _reset (self):
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
        
        self.checked = None
        self.opchecked = None
        
        self.arBoard = array("B", [0]*64)
        
        self.hash = 0
        self.pawnhash = 0
        
        ########################################################################
        #  The format of history is a list of tupples of the following fields  #
        #  move:       The move that was applied to get the position           #
        #  tpiece:     The piece the move captured, == EMPTY for normal moves  #
        #  enpassant:  cord which can be captured by enpassant or None         #
        #  castling:   The castling availability in the position               #
        #  hash:       The hash of the position                                #
        #  fifty:      A counter for the fifty moves rule                      #
        ########################################################################
        self.history = []
    
    def applyFen (self, fenstr):
        """ Applies the fenstring to the board.
            If the string is not properly
            written a SyntaxError will be raised, having its message ending in
            Pos(%d) specifying the string index of the problem.
            if an error is found, no changes will be made to the board. """
        
        # Get information
        
        parts = fenstr.split()
        
        if len(parts) > 6:
            raise SyntaxError, "Can't have more than 6 fields in fenstr. "+ \
                               "Pos(%d)" % fenstr.find(parts[6])
        
        if STRICT_FEN and len(parts) != 6:
            raise SyntaxError, "Needs 6 fields in fenstr. Pos(%d)" % len(fenstr)
        
        elif len(parts) < 4:
            raise SyntaxError, "Needs at least 6 fields in fenstr. Pos(%d)" % \
                                                                     len(fenstr)
        
        elif len(parts) >= 6:
            pieceChrs, colChr, castChr, epChr, fiftyChr, moveNoChr = parts[:6]
        
        elif len(parts) == 5:
            pieceChrs, colChr, castChr, epChr, fiftyChr == parts
            moveNoChr = "1"
        
        else:
            pieceChrs, colChr, castChr, epChr = parts
            fiftyChr = "0"
            moveNoChr = "1"
        
        # Try to validate some information
        # This should be expanded and perhaps moved
        
        slashes = len([c for c in pieceChrs if c == "/"])
        if slashes != 7:
            raise SyntaxError, "Needs 7 slashes in piece placement field. "+ \
                               "Pos(%d)" % fenstr.rfind("/")
        
        if not colChr.lower() in ("w", "b"):
            raise SyntaxError, "Active color field must be one of w or b. "+ \
                               "Pos(%d)" % fenstr.find(len(pieceChrs), colChr)
        
        if epChr != "-" and not epChr.upper() in cordDic:
            raise SyntaxError, "En passant cord is not legal. "+ \
                               "Pos(%d)" %  fenstr.rfind(epChr)
        
        # Reset this board
        
        self._reset()
        
        # Parse piece placement field
        
        for r, rank in enumerate(pieceChrs.split("/")):
            cord = (7-r)*8
            for char in rank:
                if char.isdigit():
                    cord += int(char)
                else:
                    color = char.islower() and BLACK or WHITE
                    piece = reprSign.index(char.upper())
                    self._addPiece(cord, piece, color)
                    cord += 1
        
        # Parse active color field
        
        if colChr.lower() == "w":
            self.setColor (WHITE)
        else: self.setColor (BLACK)
        
        # Parse castling availability
        
        castling = 0
        for char in castChr:
            if char == "K":
                castling |= W_OO
            elif char == "Q":
                castling |= W_OOO
            elif char == "k":
                castling |= B_OO
            elif char == "q":
                castling |= B_OOO
        self.setCastling(castling)
        
        # Parse en passant target sqaure
        
        if epChr == "-":
            self.setEnpassant (None) 
        else: self.setEnpassant(cordDic[epChr.upper()])
        
        # Parse halfmove clock field
        
        self.fifty = int(fiftyChr)
        
        # Parse halfmove clock field
        
        self.fifty = int(fiftyChr)
        
        # Parse fullmove number
        
        self.history = [None]*int(moveNoChr)
        
        self.updateBoard()
    
    def isChecked (self):
        if self.checked == None:
            kingcord = self.kings[self.color]
            self.checked = isAttacked (self, kingcord, 1-self.color)
        return self.checked
    
    def opIsChecked (self):
        if self.opchecked == None:
            kingcord = self.kings[1-self.color]
            self.opchecked = isAttacked (self, kingcord, self.color)
        return self.opchecked
        
    def _addPiece (self, cord, piece, color):
        self.boards[color][piece] = \
                setBit(self.boards[color][piece], cord)
        self.blocker90 = setBit(self.blocker90, r90[cord])
        self.blocker45 = setBit(self.blocker45, r45[cord])
        self.blocker315 = setBit(self.blocker315, r315[cord])
        
        if piece == PAWN:
            self.pawnhash ^= pieceHashes[color][PAWN][cord]
        elif piece == KING:
            self.kings[color] = cord
        
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
    
    def _move (self, fcord, tcord, piece, color):
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
    
    def setCastling (self, castling):
        if self.castling == castling: return
        
        if castling & W_OO != self.castling & W_OO:
            self.hash ^= W_OOHash
        if castling & W_OOO != self.castling & W_OOO:
            self.hash ^= W_OOOHash
        if castling & B_OO != self.castling & B_OO:
            self.hash ^= B_OOHash
        if castling & B_OOO != self.castling & B_OOO:
            self.hash ^= B_OOOHash
            
        self.castling = castling
    
    def setEnpassant (self, epcord):
        if self.enpassant == epcord: return
        if self.enpassant != None:
            self.hash ^= epHashes[self.enpassant]
        if epcord != None:
            self.hash ^= epHashes[epcord]
        self.enpassant = epcord
    
    def applyMove (self, move):
        flag = move >> 12
        fcord = (move >> 6) & 63
        tcord = move & 63
        
        fpiece = self.arBoard[fcord]
        tpiece = self.arBoard[tcord]
        
        opcolor = 1-self.color
        
        # Update history
        self.history.append (
            (move, tpiece, self.enpassant, self.castling,
            self.hash, self.fifty, self.checked, self.opchecked)
        )
        
        self.opchecked = None
        self.checked = None
        
        # Capture
        if tpiece != EMPTY:
            self._removePiece(tcord, tpiece, opcolor)
        
        if fpiece == PAWN:

            if flag == ENPASSANT:
                takenPawnC = self.enpassant + (self.color == WHITE and -8 or 8)
                self._removePiece (takenPawnC, PAWN, opcolor)
                
            elif flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                          BISHOP_PROMOTION, KNIGHT_PROMOTION):
                piece = flag - 3 # The flags has values: 8, 7, 6, 5
                self._removePiece(fcord, PAWN, self.color)
                self._addPiece(tcord, piece, self.color)
        
        if fpiece == PAWN and abs(fcord-tcord) == 16:
            self.setEnpassant ((fcord + tcord) / 2)
        else: self.setEnpassant (None)
        
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
                if tcord == H8:
                    if self.castling & B_OO:
                        self.hash ^= B_OOHash
                        self.castling &= ~B_OO
            
                elif tcord == A8:
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
                if tcord == H1:
                    if self.castling & W_OO:
                        self.hash ^= W_OOHash
                        self.castling &= ~W_OO
                    
                elif tcord == A1:
                    if self.castling & W_OOO:
                        self.hash ^= W_OOOHash
                        self.castling &= ~W_OOO
        
        if not flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                        BISHOP_PROMOTION, KNIGHT_PROMOTION):
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
        move, cpiece, enpassant, castling, \
        hash, fifty, checked, opchecked = self.history.pop()
        
        flag = move >> 12
        fcord = (move >> 6) & 63
        tcord = move & 63
        
        tpiece = self.arBoard[tcord]
        
        self._removePiece (tcord, tpiece, color)
        
        # Put back captured piece
        if cpiece != EMPTY:
            self._addPiece (tcord, cpiece, opcolor)
       	    if flag in (QUEEN_PROMOTION, ROOK_PROMOTION,
                        BISHOP_PROMOTION, KNIGHT_PROMOTION):
                self._addPiece (fcord, PAWN, color)
       	    else: self._addPiece (fcord, tpiece, color)
       	
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
            self._move (rookt, rookf, ROOK, color)
        
        self.setColor(color)
        self.updateBoard ()
        
        self.checked = checked
        self.opchecked = opchecked
        self.enpassant = enpassant
        self.castling = castling
        self.hash = hash
        self.fifty = fifty
        
    def __hash__ (self):
        return self.hash
    
    def __repr__ (self):
        b = reprColor[self.color] + " "
        b += (str(self.castling) or "-") + " "
        b += self.enpassant != None and reprCord[self.enpassant] or "-"
        b += "\n"
        rows = [self.arBoard[i:i+8] for i in range(0,64,8)][::-1]
        for r, row in enumerate(rows):
            for i, piece in enumerate(row):
                if piece != EMPTY:
                    sign = reprSign[piece]
                    if bitPosArray[(7-r)*8+i] & self.friends[WHITE]:
                        sign = sign.upper()
                    else: sign = sign.lower()
                    b += sign
                else: b += "."
                b += " "
            b += "\n"
        return b

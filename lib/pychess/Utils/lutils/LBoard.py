
from array import array

from pychess.Utils.const import *
from ldata import *
from attack import isAttacked
from bitboard import *
from threading import RLock
from copy import deepcopy

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
STRICT_FEN = False

################################################################################
# LBoard                                                                       #
################################################################################

class LBoard:
    def __init__ (self, variant):
        self.variant = variant
        self._reset()
    
    def _reset (self):
        self.blocker = createBoard(0)
        
        self.friends = [createBoard(0)]*2
        self.kings = [-1]*2
        self.boards = [[createBoard(0)]*7 for i in range(2)]
        
        self.enpassant = -1
        self.color = WHITE
        self.castling = B_OOO | B_OO | W_OOO | W_OO
        self.hasCastled = [False, False]
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

        # initial cords of rooks and kings for castling in Chess960
        if self.variant == FISCHERRANDOMCHESS:
            self.ini_kings = [None, None]
            self.ini_rooks = [[None, None], [None, None]]
        else:
            self.ini_kings = [E1, E8]
            self.ini_rooks = [[A1, H1], [A8, H8]]
    
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
            pieceChrs, colChr, castChr, epChr, fiftyChr = parts
            moveNoChr = "1"
        
        else:
            pieceChrs, colChr, castChr, epChr = parts
            fiftyChr = "0"
            moveNoChr = "1"
        
        # Try to validate some information
        # TODO: This should be expanded and perhaps moved
        
        slashes = len([c for c in pieceChrs if c == "/"])
        if slashes != 7:
            raise SyntaxError, "Needs 7 slashes in piece placement field. "+ \
                               "Pos(%d)" % fenstr.rfind("/")
        
        if not colChr.lower() in ("w", "b"):
            raise SyntaxError, "Active color field must be one of w or b. "+ \
                               "Pos(%d)" % fenstr.find(len(pieceChrs), colChr)
        
        if epChr != "-" and not epChr in cordDic:
            raise SyntaxError, ("En passant cord %s is not legal. "+ \
                                "Pos(%d) - %s") % (epChr, fenstr.rfind(epChr), \
                                 fenstr)
        
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
                    if moveNoChr == "1" and \
                        self.variant == FISCHERRANDOMCHESS:
                            if piece == KING:
                                self.ini_kings[color] = cord
                            elif piece == ROOK:
                                if self.ini_rooks[color][0] is None:
                                    self.ini_rooks[color][0] = cord
                                else:
                                    self.ini_rooks[color][1] = cord
                    cord += 1
        
        # Help tests/movegen.py in positions having no 4 rooks
        if self.variant == FISCHERRANDOMCHESS:
            if self.ini_rooks[0][0] is None:
                self.ini_rooks[0][0] = A1
            if self.ini_rooks[0][1] is None:
                self.ini_rooks[0][1] = H1
            if self.ini_rooks[1][0] is None:
                self.ini_rooks[1][0] = A8
            if self.ini_rooks[1][1] is None:
                self.ini_rooks[1][1] = H8

        # Parse active color field
        
        if colChr.lower() == "w":
            self.setColor (WHITE)
        else: self.setColor (BLACK)
        
        # Parse castling availability

        castling = 0
        for char in castChr:
            if self.variant == FISCHERRANDOMCHESS:
                if char in reprFile:
                    if char < reprCord[self.kings[BLACK]][0]:
                        castling |= B_OOO
                    else:
                        castling |= B_OO
                elif char in [c.upper() for c in reprFile]:
                    if char < reprCord[self.kings[WHITE]][0].upper():
                        castling |= W_OOO
                    else:
                        castling |= W_OO
            else:
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
        else: self.setEnpassant(cordDic[epChr])
        
        # Parse halfmove clock field
        
        self.fifty = max(int(fiftyChr),0)
        
        # Parse fullmove number
        
        movenumber = int(moveNoChr)*2 -2
        if self.color == BLACK: movenumber += 1
        self.history = [None]*movenumber
        
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
        
        if piece == PAWN:
            #assert not (color == WHITE and cord > 55)
            #assert not (color == BLACK and cord < 8)
            self.pawnhash ^= pieceHashes[color][PAWN][cord]
        elif piece == KING:
            self.kings[color] = cord
        
        self.hash ^= pieceHashes[color][piece][cord]
        self.arBoard[cord] = piece
    
    def _removePiece (self, cord, piece, color):
        self.boards[color][piece] = \
                clearBit(self.boards[color][piece], cord)
        
        if piece == PAWN:
            self.pawnhash ^= pieceHashes[color][PAWN][cord]
        
        self.hash ^= pieceHashes[color][piece][cord]
        self.arBoard[cord] = EMPTY
    
    def _move (self, fcord, tcord, piece, color):
        """ Moves the piece at fcord to tcord. """
        
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
        self.pawnhash ^= colorHash
    
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
            if self.variant == FISCHERRANDOMCHESS:
                # don't capture _our_ piece when castling king steps on rook!
                if flag not in (KING_CASTLE, QUEEN_CASTLE):
                    self._removePiece(tcord, tpiece, opcolor)
            else:
                self._removePiece(tcord, tpiece, opcolor)
        
        if fpiece == PAWN:

            if flag == ENPASSANT:
                takenPawnC = tcord + (self.color == WHITE and -8 or 8)
                self._removePiece (takenPawnC, PAWN, opcolor)
                
            elif flag in PROMOTIONS:
                piece = flag - 2 # The flags has values: 7, 6, 5, 4
                self._removePiece(fcord, PAWN, self.color)
                self._addPiece(tcord, piece, self.color)
                
        if fpiece == PAWN and abs(fcord-tcord) == 16:
            self.setEnpassant ((fcord + tcord) / 2)
        else: self.setEnpassant (None)
        
        if flag in (KING_CASTLE, QUEEN_CASTLE):
            if flag == QUEEN_CASTLE:
                if self.variant == FISCHERRANDOMCHESS:
                    if self.color == WHITE:
                        rookf = self.ini_rooks[0][0]
                        rookt = D1
                    else:
                        rookf = self.ini_rooks[1][0]
                        rookt = D8
                    # don't move our rook yet
                else:
                    rookf = fcord - 4
                    rookt = fcord - 1
                    self._move (rookf, rookt, ROOK, self.color)
            else:
                if self.variant == FISCHERRANDOMCHESS:
                    if self.color == WHITE:
                        rookf = self.ini_rooks[0][1]
                        rookt = F1
                    else:
                        rookf = self.ini_rooks[1][1]
                        rookt = F8
                    # don't move our rook yet
                else:
                    rookf = fcord + 3
                    rookt = fcord + 1
                    self._move (rookf, rookt, ROOK, self.color)
            self.hasCastled[self.color] = True
        
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
                if fcord == self.ini_rooks[0][1]: #H1
                    if self.castling & W_OO:
                        self.hash ^= W_OOHash
                        self.castling &= ~W_OO
                    
                elif fcord == self.ini_rooks[0][0]: #A1
                    if self.castling & W_OOO:
                        self.hash ^= W_OOOHash
                        self.castling &= ~W_OOO
            
            if tpiece == ROOK:
                if tcord == self.ini_rooks[1][1]: #H8
                    if self.castling & B_OO:
                        self.hash ^= B_OOHash
                        self.castling &= ~B_OO
            
                elif tcord == self.ini_rooks[1][0]: #A8
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
                if fcord == self.ini_rooks[1][1]: #H8
                    if self.castling & B_OO:
                        self.hash ^= B_OOHash
                        self.castling &= ~B_OO
            
                elif fcord == self.ini_rooks[1][0]: #A8
                    if self.castling & B_OOO:
                        self.hash ^= B_OOOHash
                        self.castling &= ~B_OOO
            
            if tpiece == ROOK:
                if tcord == self.ini_rooks[0][1]: #H1
                    if self.castling & W_OO:
                        self.hash ^= W_OOHash
                        self.castling &= ~W_OO
                    
                elif tcord == self.ini_rooks[0][0]: #A1
                    if self.castling & W_OOO:
                        self.hash ^= W_OOOHash
                        self.castling &= ~W_OOO
        
        if not flag in PROMOTIONS:
            if self.variant == FISCHERRANDOMCHESS:
                if flag in (KING_CASTLE, QUEEN_CASTLE):
                    if tpiece == EMPTY:
                        self._move(fcord, tcord, KING, self.color)
                        self._move(rookf, rookt, ROOK, self.color)
                    else:
                        self._removePiece(rookf, ROOK, self.color)
                        if flag == KING_CASTLE:
                            self._move(fcord, rookt+1, KING, self.color)
                        else:
                            self._move(fcord, rookt-1, KING, self.color)
                        self._addPiece(rookt, ROOK, self.color)
                else:
                    self._move(fcord, tcord, fpiece, self.color)
            else:
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
        
        if self.variant == FISCHERRANDOMCHESS:
            if flag in (KING_CASTLE, QUEEN_CASTLE):
                if color == WHITE:
                    if flag == QUEEN_CASTLE:
                        rookf = self.ini_rooks[0][0]
                        rookt = D1
                    else:
                        rookf = self.ini_rooks[0][1]
                        rookt = F1
                else:
                    if flag == QUEEN_CASTLE:
                        rookf = self.ini_rooks[1][0]
                        rookt = D8
                    else:
                        rookf = self.ini_rooks[1][1]
                        rookt = F8
                if cpiece == EMPTY:
                    self._removePiece (tcord, KING, color)
                else:
                    if flag == KING_CASTLE:
                        self._removePiece (rookt+1, KING, color)
                    else:
                        self._removePiece (rookt-1, KING, color)
            else:
                self._removePiece (tcord, tpiece, color)
        else:
            self._removePiece (tcord, tpiece, color)

        # Put back rook moved by castling
        if flag in (KING_CASTLE, QUEEN_CASTLE):
            if self.variant == FISCHERRANDOMCHESS:
                self._move (rookt, rookf, ROOK, color)
            else:
                if flag == QUEEN_CASTLE:
                    rookf = fcord - 4
                    rookt = fcord - 1
                else:
                    rookf = fcord + 3
                    rookt = fcord + 1
                self._move (rookt, rookf, ROOK, color)
            self.hasCastled[color] = False
        
        # Put back captured piece
        if cpiece != EMPTY:
            if flag in PROMOTIONS:
                self._addPiece (tcord, cpiece, opcolor)
                self._addPiece (fcord, PAWN, color)
            else:
                if self.variant == FISCHERRANDOMCHESS:
                    if flag in (KING_CASTLE, QUEEN_CASTLE):
                        if flag == KING_CASTLE:
                            self._addPiece (fcord, KING, color)
                        else:
                            self._addPiece (fcord, KING, color)
                    else:
                        self._addPiece (tcord, cpiece, opcolor)
                        self._addPiece (fcord, tpiece, color)
                else:
                    self._addPiece (tcord, cpiece, opcolor)
                    self._addPiece (fcord, tpiece, color)
        
        # Put back piece captured by enpassant
        elif flag == ENPASSANT:
            epcord = color == WHITE and tcord - 8 or tcord + 8
            self._addPiece (epcord, PAWN, opcolor)
            self._addPiece (fcord, PAWN, color)
            
        # Put back promoted pawn
        elif flag in PROMOTIONS:
            self._addPiece (fcord, PAWN, color)
        # Put back moved piece
        else:
            self._addPiece (fcord, tpiece, color)
        
        
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
    
    def reprCastling (self):
        if not self.castling:
            return "-"
        else:
            strs = []
            if self.variant == FISCHERRANDOMCHESS:
                if self.castling & W_OO:
                    strs.append(reprCord[self.ini_rooks[0][1]][0].upper())
                if self.castling & W_OOO:
                    strs.append(reprCord[self.ini_rooks[0][0]][0].upper())
                if self.castling & B_OO:
                    strs.append(reprCord[self.ini_rooks[1][1]][0])
                if self.castling & B_OOO:
                    strs.append(reprCord[self.ini_rooks[1][0]][0])
            else:
                if self.castling & W_OO:
                    strs.append("K")
                if self.castling & W_OOO:
                    strs.append("Q")
                if self.castling & B_OO:
                    strs.append("k")
                if self.castling & B_OOO:
                    strs.append("q")
            return "".join(strs)
    
    def __repr__ (self):
        b = reprColor[self.color] + " "
        b += self.reprCastling() + " "
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
    
    def asFen (self):
        fenstr = []
        
        rows = [self.arBoard[i:i+8] for i in range(0,64,8)][::-1]
        for r, row in enumerate(rows):
            empty = 0
            for i, piece in enumerate(row):
                if piece != EMPTY:
                    if empty > 0:
                        fenstr.append(str(empty))
                        empty = 0
                    sign = reprSign[piece]
                    if bitPosArray[(7-r)*8+i] & self.friends[WHITE]:
                        sign = sign.upper()
                    else: sign = sign.lower()
                    fenstr.append(sign)
                else:
                    empty += 1
            if empty > 0:
                fenstr.append(str(empty))
            if r != 7:
                fenstr.append("/")
        
        fenstr.append(" ")
    
        fenstr.append(self.color == WHITE and "w" or "b")
        fenstr.append(" ")
        
        fenstr.append(self.reprCastling())
        fenstr.append(" ")
        
        if not self.enpassant:
            fenstr.append("-")
        else:
            fenstr.append(reprCord[self.enpassant])
        fenstr.append(" ")
        
        fenstr.append(str(self.fifty))
        fenstr.append(" ")
        
        fullmove = (len(self.history))/2 + 1
        fenstr.append(str(fullmove))
        
        return "".join(fenstr)
    
    def clone (self):
        copy = LBoard(self.variant)
        copy.blocker = self.blocker
        
        copy.friends = self.friends[:]
        copy.kings = self.kings[:]
        copy.boards = [self.boards[WHITE][:], self.boards[BLACK][:]]
        
        copy.enpassant = self.enpassant
        copy.color = self.color
        copy.castling = self.castling
        copy.hasCastled = self.hasCastled[:]
        copy.fifty = self.fifty
        
        copy.checked = self.checked
        copy.opchecked = self.opchecked
        
        copy.arBoard = self.arBoard[:]
        
        copy.hash = self.hash
        copy.pawnhash = self.pawnhash
        
        # We don't need to deepcopy the tupples, as they are imutable
        copy.history = self.history[:]
        
        copy.ini_kings = self.ini_kings[:]
        copy.ini_rooks = [self.ini_rooks[0][:], self.ini_rooks[1][:]]
        return copy

from array import array

from pychess.Utils.const import *
from pychess.Utils.repr import reprColor
from ldata import *
from attack import isAttacked
from bitboard import *
from PolyglotHash import *

################################################################################
# FEN                                                                          #
################################################################################

# This will cause applyFen to raise an exception, if halfmove clock and fullmove
# number is not specified
STRICT_FEN = False

# Final positions of castled kings and rooks
fin_kings = ((C1,G1),(C8,G8))
fin_rooks = ((D1,F1),(D8,F8))

################################################################################
# LBoard                                                                       #
################################################################################

class LBoard:
    ini_kings = (E1, E8)
    ini_rooks = ((A1, H1), (A8, H8))

    def __init__ (self, variant=NORMALCHESS):
        self.variant = variant

        self.nags = []
        # children can contain comments and variations
        # variations are lists of lboard objects
        self.children = []
        
        # the next and prev lboard objects in the variation list
        self.next = None
        self.prev = None
        
        # The high level owner Board (with Piece objects) in gamemodel
        self.pieceBoard = None

    @property
    def lastMove (self):
        return self.hist_move[-1] if len(self.hist_move) > 0 else None

    def repetitionCount (self, drawThreshold=3):
        rc = 1
        for ply in xrange(4, 1+min(len(self.hist_hash), self.fifty), 2):
            if self.hist_hash[-ply] == self.hash:
                rc += 1
                if rc >= drawThreshold: break
        return rc
    
    def applyFen (self, fenstr):
        """ Applies the fenstring to the board.
            If the string is not properly
            written a SyntaxError will be raised, having its message ending in
            Pos(%d) specifying the string index of the problem.
            if an error is found, no changes will be made to the board. """

        assert not hasattr(self, "boards"), "The applyFen() method can be used on new LBoard objects only!"

        # Set board to empty on Black's turn (which Polyglot-hashes to 0)
        self.blocker = createBoard(0)
        
        self.friends = [createBoard(0)]*2
        self.kings = [-1]*2
        self.boards = [[createBoard(0)]*7 for i in range(2)]
        
        self.enpassant = None            # cord which can be captured by enpassant or None
        self.color = BLACK
        self.castling = 0                # The castling availability in the position
        self.hasCastled = [False, False]
        self.fifty = 0                   # A ply counter for the fifty moves rule
        self.plyCount = 0
        
        self.checked = None
        self.opchecked = None
        
        self.arBoard = array("B", [0]*64)
        
        self.hash = 0
        self.pawnhash = 0
        
        #  Data from the position's history:
        self.hist_move = []      # The move that was applied to get the position
        self.hist_tpiece = []    # The piece the move captured, == EMPTY for normal moves
        self.hist_enpassant = []
        self.hist_castling = []
        self.hist_hash = []
        self.hist_fifty = []
        self.hist_checked = []
        self.hist_opchecked = []

        # initial cords of rooks and kings for castling in Chess960
        if self.variant == FISCHERRANDOMCHESS:
            self.ini_kings = [None, None]
            self.ini_rooks = [[None, None], [None, None]]

        #elif self.variant == CRAZYHOUSECHESS:
        self.promoted = array('B', [0]*64)
        self.holding = [{PAWN:0, KNIGHT:0, BISHOP:0, ROOK:0, QUEEN:0},
                        {PAWN:0, KNIGHT:0, BISHOP:0, ROOK:0, QUEEN:0}]
        self.capture_promoting = False
        self.hist_capture_promoting = []
    
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
        
        if (not 'k' in pieceChrs) or (not 'K' in pieceChrs):
            raise SyntaxError, "FEN needs at least 'k' and 'K' in piece placement field."
        
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

            if self.variant == FISCHERRANDOMCHESS:
                # Save ranks fo find outermost rooks
                # if KkQq was used in castling rights
                if r == 0:
                    rank8 = rank
                elif r == 7:
                    rank1 = rank

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
                        self.ini_rooks[1][0] = reprFile.index(char) + 56
                    else:
                        castling |= B_OO
                        self.ini_rooks[1][1] = reprFile.index(char) + 56
                    self.ini_kings[BLACK] = self.kings[BLACK]
                elif char in [c.upper() for c in reprFile]:
                    if char < reprCord[self.kings[WHITE]][0].upper():
                        castling |= W_OOO
                        self.ini_rooks[0][0] = reprFile.index(char.lower())
                    else:
                        castling |= W_OO
                        self.ini_rooks[0][1] = reprFile.index(char.lower())
                    self.ini_kings[WHITE] = self.kings[WHITE]
                elif char == "K":
                    castling |= W_OO
                    self.ini_rooks[0][1] = rank1.rfind('R')
                    self.ini_kings[WHITE] = self.kings[WHITE]
                elif char == "Q":
                    castling |= W_OOO
                    self.ini_rooks[0][0] = rank1.find('R')
                    self.ini_kings[WHITE] = self.kings[WHITE]
                elif char == "k":
                    castling |= B_OO
                    self.ini_rooks[1][1] = rank8.rfind('r') + 56
                    self.ini_kings[BLACK] = self.kings[BLACK]
                elif char == "q":
                    castling |= B_OOO
                    self.ini_rooks[1][0] = rank8.find('r') + 56
                    self.ini_kings[BLACK] = self.kings[BLACK]
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
        self.plyCount = movenumber
    
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
        _setBit = setBit
        self.boards[color][piece] = _setBit(self.boards[color][piece], cord)
        self.friends[color] = _setBit(self.friends[color], cord)
        self.blocker = _setBit(self.blocker, cord)
        
        if piece == PAWN:
            self.pawnhash ^= pieceHashes[color][PAWN][cord]
        elif piece == KING:
            self.kings[color] = cord
        self.hash ^= pieceHashes[color][piece][cord]
        self.arBoard[cord] = piece
    
    def _removePiece (self, cord, piece, color):
        _clearBit = clearBit
        self.boards[color][piece] = _clearBit(self.boards[color][piece], cord)
        self.friends[color] = _clearBit(self.friends[color], cord)
        self.blocker = _clearBit(self.blocker, cord)
        
        if piece == PAWN:
            self.pawnhash ^= pieceHashes[color][PAWN][cord]
        
        self.hash ^= pieceHashes[color][piece][cord]
        self.arBoard[cord] = EMPTY
    
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
        # Strip the square if there's no adjacent enemy pawn to make the capture
        if epcord != None:
            sideToMove = (epcord >> 3 == 2 and BLACK or WHITE)
            fwdPawns = self.boards[sideToMove][PAWN]
            if sideToMove == WHITE:
                fwdPawns >>= 8
            else:
                fwdPawns <<= 8
            pawnTargets  = (fwdPawns & ~fileBits[0]) << 1;
            pawnTargets |= (fwdPawns & ~fileBits[7]) >> 1;
            if not pawnTargets & bitPosArray[epcord]:
                epcord = None

        if self.enpassant == epcord: return
        if self.enpassant != None:
            self.hash ^= epHashes[self.enpassant & 7]
        if epcord != None:
            self.hash ^= epHashes[epcord & 7]
        self.enpassant = epcord
    
    def applyMove (self, move):
        flag = move >> 12

        fcord = (move >> 6) & 63
        tcord = move & 63
        
        fpiece = fcord if flag==DROP else self.arBoard[fcord]
        tpiece = self.arBoard[tcord]
        
        color = self.color
        opcolor = 1-self.color
        
        self.hist_move.append(move)
        self.hist_enpassant.append(self.enpassant)
        self.hist_castling.append(self.castling)
        self.hist_hash.append(self.hash)
        self.hist_fifty.append(self.fifty)
        self.hist_checked.append(self.checked)
        self.hist_opchecked.append(self.opchecked)
        if self.variant == CRAZYHOUSECHESS:
            self.hist_capture_promoting.append(self.capture_promoting)
         
        self.opchecked = None
        self.checked = None

        if flag == NULL_MOVE:
            self.setColor(opcolor)
            return move

        # Castling moves can be represented strangely, so normalize them.
        if flag in (KING_CASTLE, QUEEN_CASTLE):
            side = flag - QUEEN_CASTLE
            fpiece = KING
            tpiece = EMPTY # In FRC, there may be a rook there, but the king doesn't capture it.
            fcord = self.ini_kings[color]
            tcord = fin_kings[color][side]
            rookf = self.ini_rooks[color][side]
            rookt = fin_rooks[color][side]

        # Capture
        if tpiece != EMPTY:
            print "The captured piece is:", reprSign[tpiece]
            self._removePiece(tcord, tpiece, opcolor)
            if self.variant == CRAZYHOUSECHESS:
                if self.promoted[tcord]:
                    self.holding[color][PAWN] += 1
                    self.capture_promoting = True
                else:
                    self.holding[color][tpiece] += 1
                    self.capture_promoting = False
                self.promoted[tcord] = 0
        
        self.hist_tpiece.append(tpiece)
        
        # Remove moving piece(s), then add them at their destination.
        if flag == DROP:
            assert self.holding[color][fpiece] > 0
            self.holding[color][fpiece] -= 1
        else:
            self._removePiece(fcord, fpiece, color)

        if flag in (KING_CASTLE, QUEEN_CASTLE):
            self._removePiece (rookf, ROOK, color)
            self._addPiece (rookt, ROOK, color)
            self.hasCastled[color] = True
        
        if flag == ENPASSANT:
            takenPawnC = tcord + (color == WHITE and -8 or 8)
            self._removePiece (takenPawnC, PAWN, opcolor)
            if self.variant == CRAZYHOUSECHESS:
                self.holding[color][PAWN] += 1
        elif flag in PROMOTIONS:
            # Pretend the pawn changes into a piece before reaching its destination.
            fpiece = flag - 2

        if self.variant == CRAZYHOUSECHESS:
            if flag in PROMOTIONS:
                self.promoted[tcord] = 1
            else:
                if self.promoted[fcord]:
                    self.promoted[fcord] = 0
                    self.promoted[tcord] = 1
                
        self._addPiece(tcord, fpiece, color)

        if fpiece == PAWN and abs(fcord-tcord) == 16:
            self.setEnpassant ((fcord + tcord) / 2)
        else: self.setEnpassant (None)
        
        if tpiece == EMPTY and fpiece != PAWN:
            self.fifty += 1
        else:
            self.fifty = 0
        
        # Clear castle flags
        castling = self.castling
        if fpiece == KING:
            castling &= ~CAS_FLAGS[color][0]
            castling &= ~CAS_FLAGS[color][1]
        elif fpiece == ROOK:
            if fcord == self.ini_rooks[color][0]:
                castling &= ~CAS_FLAGS[color][0]
            elif fcord == self.ini_rooks[color][1]:
                castling &= ~CAS_FLAGS[color][1]
        if tpiece == ROOK:
            if tcord == self.ini_rooks[opcolor][0]:
                castling &= ~CAS_FLAGS[opcolor][0]
            elif tcord == self.ini_rooks[opcolor][1]:
                castling &= ~CAS_FLAGS[opcolor][1]
        self.setCastling(castling)

        self.setColor(opcolor)
        self.plyCount += 1
    
    def popMove (self):
        # Note that we remove the last made move, which was not made by boards
        # current color, but by its opponent
        color = 1 - self.color
        opcolor = self.color
        
        move = self.hist_move.pop()
        cpiece = self.hist_tpiece.pop()
        if self.variant == CRAZYHOUSECHESS:
            capture_promoting = self.hist_capture_promoting.pop()
            
        flag = move >> 12
        
        if flag == NULL_MOVE:
            self.setColor(color)
            return
            
        fcord = (move >> 6) & 63
        tcord = move & 63
        tpiece = self.arBoard[tcord]
        
        # Castling moves can be represented strangely, so normalize them.
        if flag in (KING_CASTLE, QUEEN_CASTLE):
            side = flag - QUEEN_CASTLE
            tpiece = KING
            fcord = self.ini_kings[color]
            tcord = fin_kings[color][side]
            rookf = self.ini_rooks[color][side]
            rookt = fin_rooks[color][side]
            self._removePiece (tcord, tpiece, color)
            self._removePiece (rookt, ROOK, color)
            self._addPiece (rookf, ROOK, color)
            self.hasCastled[color] = False
        else:
            self._removePiece (tcord, tpiece, color)
        
        # Put back captured piece
        if cpiece != EMPTY:
            self._addPiece (tcord, cpiece, opcolor)
            print "put back captured piece:", reprSign[cpiece]
            if self.variant == CRAZYHOUSECHESS:
                if capture_promoting:
                    assert self.holding[color][PAWN] > 0
                    self.holding[color][PAWN] -= 1
                else:
                    assert self.holding[color][cpiece] > 0
                    self.holding[color][cpiece] -= 1
                
        # Put back piece captured by enpassant
        if flag == ENPASSANT:
            epcord = color == WHITE and tcord - 8 or tcord + 8
            self._addPiece (epcord, PAWN, opcolor)
            if self.variant == CRAZYHOUSECHESS:
                assert self.holding[color][PAWN] > 0
                self.holding[color][PAWN] -= 1
            
        # Un-promote pawn
        if flag in PROMOTIONS:
            tpiece = PAWN

        # Put back moved piece
        if flag == DROP:
            self.holding[color][tpiece] += 1
        else:
            self._addPiece (fcord, tpiece, color)

        if self.variant == CRAZYHOUSECHESS:
            if flag in PROMOTIONS:
                self.promoted[tcord] = 0
            else:
                if self.promoted[tcord]:
                    self.promoted[fcord] = 1
                    self.promoted[tcord] = 0
        
        self.setColor(color)
        
        self.checked = self.hist_checked.pop()
        self.opchecked = self.hist_opchecked.pop()
        self.enpassant = self.hist_enpassant.pop()
        self.castling = self.hist_castling.pop()
        self.hash = self.hist_hash.pop()
        self.fifty = self.hist_fifty.pop()
        self.plyCount -= 1
        
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
        
        fullmove = (self.plyCount)/2 + 1
        fenstr.append(str(fullmove))
        
        return "".join(fenstr)
    
    def clone (self):
        copy = LBoard(self.variant)
        copy.blocker = self.blocker
        
        copy.friends = self.friends[:]
        copy.kings = self.kings[:]
        copy.boards = [self.boards[WHITE][:], self.boards[BLACK][:]]
        copy.arBoard = self.arBoard[:]
        
        copy.color = self.color
        copy.plyCount = self.plyCount
        copy.hasCastled = self.hasCastled[:]

        copy.enpassant = self.enpassant
        copy.castling = self.castling
        copy.hash = self.hash
        copy.pawnhash = self.pawnhash
        copy.fifty = self.fifty
        copy.checked = self.checked
        copy.opchecked = self.opchecked
        
        copy.hist_move = self.hist_move[:]
        copy.hist_tpiece = self.hist_tpiece[:]
        copy.hist_enpassant = self.hist_enpassant[:]
        copy.hist_castling = self.hist_castling[:]
        copy.hist_hash = self.hist_hash[:]
        copy.hist_fifty = self.hist_fifty[:]
        copy.hist_checked = self.hist_checked[:]
        copy.hist_opchecked = self.hist_opchecked[:]
        
        if self.variant == FISCHERRANDOMCHESS:
            copy.ini_kings = self.ini_kings[:]
            copy.ini_rooks = [self.ini_rooks[0][:], self.ini_rooks[1][:]]
        elif self.variant == CRAZYHOUSECHESS:
            copy.promoted = self.promoted[:]
            copy.holding = [self.holding[0].copy(), self.holding[1].copy()]
            copy.capture_promoting = self.capture_promoting
            copy.hist_capture_promoting = self.hist_capture_promoting[:]
            
        return copy

from __future__ import absolute_import

from pychess.compat import PY3
from pychess.Utils.const import EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, \
    ATOMICCHESS, BUGHOUSECHESS, CRAZYHOUSECHESS, CAMBODIANCHESS, MAKRUKCHESS, \
    FISCHERRANDOMCHESS, SITTUYINCHESS, WILDCASTLECHESS, WILDCASTLESHUFFLECHESS, \
    SUICIDECHESS, DROP_VARIANTS, BLACK, WHITE, FAN_PIECES, NULL_MOVE, CAS_FLAGS, \
    NORMALCHESS, \
    chrU2Sign, cordDic, reprCord, reprFile, reprSign, reprSignMakruk, reprSignSittuyin, \
    A1, A8, B1, B8, \
    C1, C8, D1, D8, \
    E1, E8, F1, F8, \
    G1, G8, H1, H8, \
    KING_CASTLE, QUEEN_CASTLE, DROP, PROMOTIONS, ENPASSANT, B_OO, B_OOO, W_OO, W_OOO
from pychess.Utils.repr import reprColor
from .ldata import FILE, fileBits
from .attack import isAttacked
from .bitboard import clearBit, setBit, bitPosArray
from .PolyglotHash import pieceHashes, epHashes, \
    W_OOHash, W_OOOHash, B_OOHash, B_OOOHash, colorHash

################################################################################
# FEN                                                                          #
################################################################################

# This will cause applyFen to raise an exception, if halfmove clock and fullmove
# number is not specified
STRICT_FEN = False

################################################################################
# LBoard                                                                       #
################################################################################


class LBoard(object):
    __hash__ = None

    ini_kings = (E1, E8)
    ini_rooks = ((A1, H1), (A8, H8))

    # Final positions of castled kings and rooks
    fin_kings = ((C1, G1), (C8, G8))
    fin_rooks = ((D1, F1), (D8, F8))

    holding = ({PAWN: 0,
                KNIGHT: 0,
                BISHOP: 0,
                ROOK: 0,
                QUEEN: 0,
                KING: 0},
               {PAWN: 0,
                KNIGHT: 0,
                BISHOP: 0,
                ROOK: 0,
                QUEEN: 0,
                KING: 0})

    def __init__(self, variant=NORMALCHESS):
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

        # This will True except in so called null_board
        # null_board act as parent of the variation
        # when we add a variation to last played board from hint panel
        self.fen_was_applied = False

    @property
    def lastMove(self):
        return self.hist_move[-1] if self.fen_was_applied and len(
            self.hist_move) > 0 else None

    def repetitionCount(self, draw_threshold=3):
        rc = 1
        for ply in range(4, 1 + min(len(self.hist_hash), self.fifty), 2):
            if self.hist_hash[-ply] == self.hash:
                rc += 1
                if rc >= draw_threshold:
                    break
        return rc

    def iniAtomic(self):
        self.hist_exploding_around = []

    def iniHouse(self):
        self.promoted = [0] * 64
        self.capture_promoting = False
        self.hist_capture_promoting = []
        self.holding = ({PAWN: 0,
                         KNIGHT: 0,
                         BISHOP: 0,
                         ROOK: 0,
                         QUEEN: 0,
                         KING: 0},
                        {PAWN: 0,
                         KNIGHT: 0,
                         BISHOP: 0,
                         ROOK: 0,
                         QUEEN: 0,
                         KING: 0})

    def iniCambodian(self):
        self.ini_kings = (D1, E8)
        self.ini_queens = (E1, D8)
        self.is_first_move = {KING: [True, True], QUEEN: [True, True]}
        self.hist_is_first_move = []

    def applyFen(self, fenstr):
        """ Applies the fenstring to the board.
            If the string is not properly
            written a SyntaxError will be raised, having its message ending in
            Pos(%d) specifying the string index of the problem.
            if an error is found, no changes will be made to the board. """

        assert not self.fen_was_applied, "The applyFen() method can be used on new LBoard objects only!"

        # Set board to empty on Black's turn (which Polyglot-hashes to 0)
        self.blocker = 0

        self.friends = [0] * 2
        self.kings = [-1] * 2
        self.boards = [[0] * 7 for i in range(2)]

        self.enpassant = None  # cord which can be captured by enpassant or None
        self.color = BLACK
        self.castling = 0  # The castling availability in the position
        self.hasCastled = [False, False]
        self.fifty = 0  # A ply counter for the fifty moves rule
        self.plyCount = 0

        self.checked = None
        self.opchecked = None

        self.arBoard = [0] * 64

        self.hash = 0
        self.pawnhash = 0

        #  Data from the position's history:
        self.hist_move = []  # The move that was applied to get the position
        self.hist_tpiece = [
        ]  # The piece the move captured, == EMPTY for normal moves
        self.hist_enpassant = []
        self.hist_castling = []
        self.hist_hash = []
        self.hist_fifty = []
        self.hist_checked = []
        self.hist_opchecked = []

        # piece counts
        self.pieceCount = [[0] * 7, [0] * 7]

        # initial cords of rooks and kings for castling in Chess960
        if self.variant == FISCHERRANDOMCHESS:
            self.ini_kings = [None, None]
            self.ini_rooks = ([None, None], [None, None])

        elif self.variant in (WILDCASTLECHESS, WILDCASTLESHUFFLECHESS):
            self.ini_kings = [None, None]
            self.fin_kings = ([None, None], [None, None])
            self.fin_rooks = ([None, None], [None, None])

        elif self.variant in DROP_VARIANTS:
            self.iniHouse()

        elif self.variant == ATOMICCHESS:
            self.iniAtomic()

        elif self.variant == CAMBODIANCHESS:
            self.iniCambodian()

            # Get information
        parts = fenstr.split()
        castChr = "-"
        epChr = "-"
        fiftyChr = "0"
        moveNoChr = "1"
        if STRICT_FEN and len(parts) != 6:
            raise SyntaxError(_("FEN needs 6 data fields. \n\n%s") % fenstr)
        elif len(parts) < 2:
            raise SyntaxError(
                _("FEN needs at least 2 data fields in fenstr. \n\n%s") %
                fenstr)
        elif len(parts) >= 6:
            pieceChrs, colChr, castChr, epChr, fiftyChr, moveNoChr = parts[:6]
        elif len(parts) == 5:
            pieceChrs, colChr, castChr, epChr, fiftyChr = parts
        elif len(parts) == 4:
            if parts[2].isdigit() and parts[3].isdigit():
                # xboard FEN usage for asian variants
                pieceChrs, colChr, fiftyChr, moveNoChr = parts
            else:
                pieceChrs, colChr, castChr, epChr = parts
        elif len(parts) == 3:
            pieceChrs, colChr, castChr = parts
        else:
            pieceChrs, colChr = parts

        # Try to validate some information
        # TODO: This should be expanded and perhaps moved

        slashes = pieceChrs.count("/")
        if slashes < 7:
            raise SyntaxError(
                _("Needs 7 slashes in piece placement field. \n\n%s") % fenstr)

        if not colChr.lower() in ("w", "b"):
            raise SyntaxError(
                _("Active color field must be one of w or b. \n\n%s") % fenstr)

        if castChr != "-":
            for Chr in castChr:
                valid_chars = "ABCDEFGHKQ" if self.variant == FISCHERRANDOMCHESS else "KQ"
                if Chr.upper() not in valid_chars:
                    if self.variant == CAMBODIANCHESS:
                        pass
                        # sjaakii uses DEde in cambodian starting fen to indicate
                        # that queens and kings are virgins (not moved yet)
                    else:
                        raise SyntaxError(_("Castling availability field is not legal. \n\n%s")
                                          % fenstr)

        if epChr != "-" and epChr not in cordDic:
            raise SyntaxError(_("En passant cord is not legal. \n\n%s") %
                              fenstr)

        # Parse piece placement field
        promoted = False
        # if there is a holding within [] we change it to BFEN style first
        if pieceChrs.endswith("]"):
            pieceChrs = pieceChrs[:-1].replace("[", "/")
        for r, rank in enumerate(pieceChrs.split("/")):
            cord = (7 - r) * 8
            for char in rank:
                if r > 7:
                    # After the 8.rank BFEN can contain holdings (captured pieces)
                    # "~" after a piece letter denotes promoted piece
                    if r == 8 and self.variant in DROP_VARIANTS:
                        color = char.islower() and BLACK or WHITE
                        piece = chrU2Sign[char.upper()]
                        self.holding[color][piece] += 1
                        continue
                    else:
                        break

                if char.isdigit():
                    cord += int(char)
                elif char == "~":
                    promoted = True
                else:
                    color = char.islower() and BLACK or WHITE
                    piece = chrU2Sign[char.upper()]
                    self._addPiece(cord, piece, color)
                    self.pieceCount[color][piece] += 1

                    if self.variant in DROP_VARIANTS and promoted:
                        self.promoted[cord] = 1
                        promoted = False

                    if self.variant == CAMBODIANCHESS:
                        if piece == KING and self.kings[
                                color] != self.ini_kings[color]:
                            self.is_first_move[KING][color] = False
                        if piece == QUEEN and cord != self.ini_queens[color]:
                            self.is_first_move[QUEEN][color] = False

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
            self.setColor(WHITE)
        else:
            self.setColor(BLACK)

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
                elif char in [c.upper() for c in reprFile]:
                    if char < reprCord[self.kings[WHITE]][0].upper():
                        castling |= W_OOO
                        self.ini_rooks[0][0] = reprFile.index(char.lower())
                    else:
                        castling |= W_OO
                        self.ini_rooks[0][1] = reprFile.index(char.lower())
                elif char == "K":
                    castling |= W_OO
                    self.ini_rooks[0][1] = rank1.rfind('R')
                elif char == "Q":
                    castling |= W_OOO
                    self.ini_rooks[0][0] = rank1.find('R')
                elif char == "k":
                    castling |= B_OO
                    self.ini_rooks[1][1] = rank8.rfind('r') + 56
                elif char == "q":
                    castling |= B_OOO
                    self.ini_rooks[1][0] = rank8.find('r') + 56
            else:
                if char == "K":
                    castling |= W_OO
                elif char == "Q":
                    castling |= W_OOO
                elif char == "k":
                    castling |= B_OO
                elif char == "q":
                    castling |= B_OOO

        if self.variant in (WILDCASTLECHESS, WILDCASTLESHUFFLECHESS,
                            FISCHERRANDOMCHESS):
            self.ini_kings[WHITE] = self.kings[WHITE]
            self.ini_kings[BLACK] = self.kings[BLACK]
            if self.variant in (WILDCASTLECHESS, WILDCASTLESHUFFLECHESS):
                if self.ini_kings[WHITE] == D1 and self.ini_kings[BLACK] == D8:
                    self.fin_kings = ([B1, F1], [B8, F8])
                    self.fin_rooks = ([C1, E1], [C8, E8])
                elif self.ini_kings[WHITE] == D1:
                    self.fin_kings = ([B1, F1], [C8, G8])
                    self.fin_rooks = ([C1, E1], [D8, F8])
                elif self.ini_kings[BLACK] == D8:
                    self.fin_kings = ([C1, G1], [B8, F8])
                    self.fin_rooks = ([D1, F1], [C8, E8])
                else:
                    self.fin_kings = ([C1, G1], [C8, G8])
                    self.fin_rooks = ([D1, F1], [D8, F8])

        self.setCastling(castling)

        # Parse en passant target sqaure

        if epChr == "-":
            self.setEnpassant(None)
        else:
            self.setEnpassant(cordDic[epChr])

        # Parse halfmove clock field

        if fiftyChr.isdigit():
            self.fifty = int(fiftyChr)
        else:
            self.fifty = 0

        # Parse fullmove number

        if moveNoChr.isdigit():
            movenumber = max(int(moveNoChr), 1) * 2 - 2
            if self.color == BLACK:
                movenumber += 1
            self.plyCount = movenumber
        else:
            self.plyCount = 1

        self.fen_was_applied = True

    def isChecked(self):
        if self.variant == SUICIDECHESS:
            return False
        elif self.variant == ATOMICCHESS:
            if not self.boards[self.color][KING]:
                return False
            if -2 < (self.kings[0] >> 3) - (self.kings[1] >> 3) < 2 and -2 < (self.kings[0] & 7) - (self.kings[1] & 7) < 2:
                return False
        elif self.variant == SITTUYINCHESS and self.plyCount < 16:
            return False
        if self.checked is None:
            kingcord = self.kings[self.color]
            self.checked = isAttacked(self,
                                      kingcord,
                                      1 - self.color,
                                      ischecked=True)
        return self.checked

    def opIsChecked(self):
        if self.variant == SUICIDECHESS:
            return False
        elif self.variant == ATOMICCHESS:
            if not self.boards[1 - self.color][KING]:
                return False
            if -2 < (self.kings[0] >> 3) - (self.kings[1] >> 3) < 2 and -2 < (self.kings[0] & 7) - (self.kings[1] & 7) < 2:
                return False
        elif self.variant == SITTUYINCHESS and self.plyCount < 16:
            return False
        if self.opchecked is None:
            kingcord = self.kings[1 - self.color]
            self.opchecked = isAttacked(self,
                                        kingcord,
                                        self.color,
                                        ischecked=True)
        return self.opchecked

    def willLeaveInCheck(self, move):
        if self.variant == SUICIDECHESS:
            return False
        board_clone = self.clone()
        board_clone.applyMove(move)
        return board_clone.opIsChecked()

    def _addPiece(self, cord, piece, color):
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

    def _removePiece(self, cord, piece, color):
        _clearBit = clearBit
        self.boards[color][piece] = _clearBit(self.boards[color][piece], cord)
        self.friends[color] = _clearBit(self.friends[color], cord)
        self.blocker = _clearBit(self.blocker, cord)

        if piece == PAWN:
            self.pawnhash ^= pieceHashes[color][PAWN][cord]

        self.hash ^= pieceHashes[color][piece][cord]
        self.arBoard[cord] = EMPTY

    def setColor(self, color):
        if color == self.color:
            return
        self.color = color
        self.hash ^= colorHash

    def setCastling(self, castling):
        if self.castling == castling:
            return

        if castling & W_OO != self.castling & W_OO:
            self.hash ^= W_OOHash
        if castling & W_OOO != self.castling & W_OOO:
            self.hash ^= W_OOOHash
        if castling & B_OO != self.castling & B_OO:
            self.hash ^= B_OOHash
        if castling & B_OOO != self.castling & B_OOO:
            self.hash ^= B_OOOHash

        self.castling = castling

    def setEnpassant(self, epcord):
        # Strip the square if there's no adjacent enemy pawn to make the capture
        if epcord is not None:
            sideToMove = (epcord >> 3 == 2 and BLACK or WHITE)
            fwdPawns = self.boards[sideToMove][PAWN]
            if sideToMove == WHITE:
                fwdPawns >>= 8
            else:
                fwdPawns <<= 8
            pawnTargets = (fwdPawns & ~fileBits[0]) << 1
            pawnTargets |= (fwdPawns & ~fileBits[7]) >> 1
            if not pawnTargets & bitPosArray[epcord]:
                epcord = None

        if self.enpassant == epcord:
            return
        if self.enpassant is not None:
            self.hash ^= epHashes[self.enpassant & 7]
        if epcord is not None:
            self.hash ^= epHashes[epcord & 7]
        self.enpassant = epcord

    # @profile
    def applyMove(self, move):
        flag = move >> 12

        fcord = (move >> 6) & 63
        tcord = move & 63

        fpiece = fcord if flag == DROP else self.arBoard[fcord]
        tpiece = self.arBoard[tcord]

        color = self.color
        opcolor = 1 - self.color
        castling = self.castling

        self.hist_move.append(move)
        self.hist_enpassant.append(self.enpassant)
        self.hist_castling.append(self.castling)
        self.hist_hash.append(self.hash)
        self.hist_fifty.append(self.fifty)
        self.hist_checked.append(self.checked)
        self.hist_opchecked.append(self.opchecked)
        if self.variant in DROP_VARIANTS:
            self.hist_capture_promoting.append(self.capture_promoting)
        if self.variant == CAMBODIANCHESS:
            self.hist_is_first_move.append({KING: self.is_first_move[KING][:],
                                            QUEEN: self.is_first_move[QUEEN][:]})

        self.opchecked = None
        self.checked = None

        if flag == NULL_MOVE:
            self.setColor(opcolor)
            self.plyCount += 1
            return move

        if self.variant == CAMBODIANCHESS:
            if fpiece == KING and self.is_first_move[KING][color]:
                self.is_first_move[KING][color] = False
            elif fpiece == QUEEN and self.is_first_move[QUEEN][color]:
                self.is_first_move[QUEEN][color] = False

        # Castling moves can be represented strangely, so normalize them.
        if flag in (KING_CASTLE, QUEEN_CASTLE):
            side = flag - QUEEN_CASTLE
            fpiece = KING
            tpiece = EMPTY  # In FRC, there may be a rook there, but the king doesn't capture it.
            fcord = self.ini_kings[color]
            if FILE(fcord) == 3 and self.variant in (WILDCASTLECHESS,
                                                     WILDCASTLESHUFFLECHESS):
                side = 0 if side == 1 else 1
            tcord = self.fin_kings[color][side]
            rookf = self.ini_rooks[color][side]
            rookt = self.fin_rooks[color][side]

        # Capture (sittuyin in place promotion is not capture move!)
        if tpiece != EMPTY and fcord != tcord:
            self._removePiece(tcord, tpiece, opcolor)
            self.pieceCount[opcolor][tpiece] -= 1
            if self.variant in DROP_VARIANTS:
                if self.promoted[tcord]:
                    if self.variant == CRAZYHOUSECHESS:
                        self.holding[color][PAWN] += 1
                    self.capture_promoting = True
                else:
                    if self.variant == CRAZYHOUSECHESS:
                        self.holding[color][tpiece] += 1
                    self.capture_promoting = False
            elif self.variant == ATOMICCHESS:
                from pychess.Variants.atomic import piecesAround
                apieces = [(fcord, fpiece, color), ]
                for acord, apiece, acolor in piecesAround(self, tcord):
                    if apiece != PAWN and acord != fcord:
                        self._removePiece(acord, apiece, acolor)
                        self.pieceCount[acolor][apiece] -= 1
                        apieces.append((acord, apiece, acolor))
                    if apiece == ROOK and acord != fcord:
                        if acord == self.ini_rooks[opcolor][0]:
                            castling &= ~CAS_FLAGS[opcolor][0]
                        elif acord == self.ini_rooks[opcolor][1]:
                            castling &= ~CAS_FLAGS[opcolor][1]
                self.hist_exploding_around.append(apieces)

        self.hist_tpiece.append(tpiece)

        # Remove moving piece(s), then add them at their destination.
        if flag == DROP:
            if self.variant in DROP_VARIANTS:
                assert self.holding[color][fpiece] > 0
            self.holding[color][fpiece] -= 1
            self.pieceCount[color][fpiece] += 1
        else:
            self._removePiece(fcord, fpiece, color)

        if flag in (KING_CASTLE, QUEEN_CASTLE):
            self._removePiece(rookf, ROOK, color)
            self._addPiece(rookt, ROOK, color)
            self.hasCastled[color] = True

        if flag == ENPASSANT:
            takenPawnC = tcord + (color == WHITE and -8 or 8)
            self._removePiece(takenPawnC, PAWN, opcolor)
            self.pieceCount[opcolor][PAWN] -= 1
            if self.variant == CRAZYHOUSECHESS:
                self.holding[color][PAWN] += 1
            elif self.variant == ATOMICCHESS:
                from pychess.Variants.atomic import piecesAround
                apieces = [(fcord, fpiece, color), ]
                for acord, apiece, acolor in piecesAround(self, tcord):
                    if apiece != PAWN and acord != fcord:
                        self._removePiece(acord, apiece, acolor)
                        self.pieceCount[acolor][apiece] -= 1
                        apieces.append((acord, apiece, acolor))
                self.hist_exploding_around.append(apieces)
        elif flag in PROMOTIONS:
            # Pretend the pawn changes into a piece before reaching its destination.
            fpiece = flag - 2
            self.pieceCount[color][fpiece] += 1
            self.pieceCount[color][PAWN] -= 1

        if self.variant in DROP_VARIANTS:
            if tpiece == EMPTY:
                self.capture_promoting = False

            if flag in PROMOTIONS:
                self.promoted[tcord] = 1
            elif flag != DROP:
                if self.promoted[fcord]:
                    self.promoted[fcord] = 0
                    self.promoted[tcord] = 1
                elif tpiece != EMPTY:
                    self.promoted[tcord] = 0

        if self.variant == ATOMICCHESS and (tpiece != EMPTY or
                                            flag == ENPASSANT):
            self.pieceCount[color][fpiece] -= 1
        else:
            self._addPiece(tcord, fpiece, color)

        if fpiece == PAWN and abs(fcord - tcord) == 16:
            self.setEnpassant((fcord + tcord) // 2)
        else:
            self.setEnpassant(None)

        if tpiece == EMPTY and fpiece != PAWN:
            self.fifty += 1
        else:
            self.fifty = 0

        # Clear castle flags
        king = self.ini_kings[color]
        wildcastle = FILE(king) == 3 and self.variant in (
            WILDCASTLECHESS, WILDCASTLESHUFFLECHESS)
        if fpiece == KING:
            castling &= ~CAS_FLAGS[color][0]
            castling &= ~CAS_FLAGS[color][1]
        elif fpiece == ROOK:
            if fcord == self.ini_rooks[color][0]:
                side = 1 if wildcastle else 0
                castling &= ~CAS_FLAGS[color][side]
            elif fcord == self.ini_rooks[color][1]:
                side = 0 if wildcastle else 1
                castling &= ~CAS_FLAGS[color][side]
        if tpiece == ROOK:
            if tcord == self.ini_rooks[opcolor][0]:
                side = 1 if wildcastle else 0
                castling &= ~CAS_FLAGS[opcolor][side]
            elif tcord == self.ini_rooks[opcolor][1]:
                side = 0 if wildcastle else 1
                castling &= ~CAS_FLAGS[opcolor][side]
        self.setCastling(castling)

        self.setColor(opcolor)
        self.plyCount += 1

    def popMove(self):
        # Note that we remove the last made move, which was not made by boards
        # current color, but by its opponent
        color = 1 - self.color
        opcolor = self.color

        move = self.hist_move.pop()
        cpiece = self.hist_tpiece.pop()

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
            if FILE(fcord) == 3 and self.variant in (WILDCASTLECHESS,
                                                     WILDCASTLESHUFFLECHESS):
                side = 0 if side == 1 else 1
            tcord = self.fin_kings[color][side]
            rookf = self.ini_rooks[color][side]
            rookt = self.fin_rooks[color][side]
            self._removePiece(tcord, tpiece, color)
            self._removePiece(rookt, ROOK, color)
            self._addPiece(rookf, ROOK, color)
            self.hasCastled[color] = False
        else:
            self._removePiece(tcord, tpiece, color)

        # Put back captured piece
        if cpiece != EMPTY and fcord != tcord:
            self._addPiece(tcord, cpiece, opcolor)
            self.pieceCount[opcolor][cpiece] += 1
            if self.variant == CRAZYHOUSECHESS:
                if self.capture_promoting:
                    assert self.holding[color][PAWN] > 0
                    self.holding[color][PAWN] -= 1
                else:
                    assert self.holding[color][cpiece] > 0
                    self.holding[color][cpiece] -= 1
            elif self.variant == ATOMICCHESS:
                apieces = self.hist_exploding_around.pop()
                for acord, apiece, acolor in apieces:
                    self._addPiece(acord, apiece, acolor)
                    self.pieceCount[acolor][apiece] += 1

                    # Put back piece captured by enpassant
        if flag == ENPASSANT:
            epcord = color == WHITE and tcord - 8 or tcord + 8
            self._addPiece(epcord, PAWN, opcolor)
            self.pieceCount[opcolor][PAWN] += 1
            if self.variant == CRAZYHOUSECHESS:
                assert self.holding[color][PAWN] > 0
                self.holding[color][PAWN] -= 1
            elif self.variant == ATOMICCHESS:
                apieces = self.hist_exploding_around.pop()
                for acord, apiece, acolor in apieces:
                    self._addPiece(acord, apiece, acolor)
                    self.pieceCount[acolor][apiece] += 1

            # Un-promote pawn
        if flag in PROMOTIONS:
            tpiece = PAWN
            self.pieceCount[color][flag - 2] -= 1
            self.pieceCount[color][PAWN] += 1

        # Put back moved piece
        if flag == DROP:
            self.holding[color][tpiece] += 1
            self.pieceCount[color][tpiece] -= 1
        else:
            if not (self.variant == ATOMICCHESS and
                    (cpiece != EMPTY or flag == ENPASSANT)):
                self._addPiece(fcord, tpiece, color)

        if self.variant in DROP_VARIANTS:
            if flag != DROP:
                if self.promoted[tcord] and (flag not in PROMOTIONS):
                    self.promoted[fcord] = 1
                if self.capture_promoting:
                    self.promoted[tcord] = 1
                else:
                    self.promoted[tcord] = 0
            self.capture_promoting = self.hist_capture_promoting.pop()

        if self.variant == CAMBODIANCHESS:
            self.is_first_move = self.hist_is_first_move.pop()

        self.setColor(color)

        self.checked = self.hist_checked.pop()
        self.opchecked = self.hist_opchecked.pop()
        self.enpassant = self.hist_enpassant.pop()
        self.castling = self.hist_castling.pop()
        self.hash = self.hist_hash.pop()
        self.fifty = self.hist_fifty.pop()
        self.plyCount -= 1

    def __eq__(self, other):
        return isinstance(other, LBoard) and \
            self.fen_was_applied and other.fen_was_applied and \
            self.hash == other.hash and self.plyCount == other.plyCount

    def __ne__(self, other):
        return not self.__eq__(other)

    def reprCastling(self):
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

    def prepr(self, ascii=False):
        if not self.fen_was_applied:
            return ("LBoard without applied FEN")
        b = "#" + reprColor[self.color] + " "
        b += self.reprCastling() + " "
        b += self.enpassant is not None and reprCord[self.enpassant] or "-"
        b += "\n# "
        rows = [self.arBoard[i:i + 8] for i in range(0, 64, 8)][::-1]
        for r, row in enumerate(rows):
            for i, piece in enumerate(row):
                if piece != EMPTY:
                    if bitPosArray[(7 - r) * 8 + i] & self.friends[WHITE]:
                        assert self.boards[WHITE][
                            piece], "self.boards doesn't match self.arBoard !!!"
                        sign = reprSign[piece] if ascii else FAN_PIECES[WHITE][
                            piece]
                    else:
                        assert self.boards[BLACK][
                            piece], "self.boards doesn't match self.arBoard !!!"
                        sign = reprSign[piece].lower(
                        ) if ascii else FAN_PIECES[BLACK][piece]
                    b += sign
                else:
                    b += "."
                b += " "
            b += "\n# "

        if self.variant in DROP_VARIANTS:
            for color in (BLACK, WHITE):
                holding = self.holding[color]
                b += "\n# [%s]" % "".join([reprSign[
                    piece] if ascii else FAN_PIECES[color][piece] * holding[
                        piece] for piece in holding if holding[piece] > 0])
        return b

    def __repr__(self):
        b = self.prepr()
        return b if PY3 else b.encode('utf8')

    def asFen(self, enable_bfen=True):
        fenstr = []

        rows = [self.arBoard[i:i + 8] for i in range(0, 64, 8)][::-1]
        for r, row in enumerate(rows):
            empty = 0
            for i, piece in enumerate(row):
                if piece != EMPTY:
                    if empty > 0:
                        fenstr.append(str(empty))
                        empty = 0
                    if self.variant in (CAMBODIANCHESS, MAKRUKCHESS):
                        sign = reprSignMakruk[piece]
                    elif self.variant == SITTUYINCHESS:
                        sign = reprSignSittuyin[piece]
                    else:
                        sign = reprSign[piece]
                    if bitPosArray[(7 - r) * 8 + i] & self.friends[WHITE]:
                        sign = sign.upper()
                    else:
                        sign = sign.lower()
                    fenstr.append(sign)
                    if self.variant in (BUGHOUSECHESS, CRAZYHOUSECHESS):
                        if self.promoted[r * 8 + i]:
                            fenstr.append("~")
                else:
                    empty += 1
            if empty > 0:
                fenstr.append(str(empty))
            if r != 7:
                fenstr.append("/")

        if self.variant in DROP_VARIANTS:
            holding_pieces = []
            for color in (BLACK, WHITE):
                holding = self.holding[color]
                for piece in holding:
                    if holding[piece] > 0:
                        if self.variant == SITTUYINCHESS:
                            sign = reprSignSittuyin[piece]
                        else:
                            sign = reprSign[piece]
                        sign = sign.upper() if color == WHITE else sign.lower()
                        holding_pieces.append(sign * holding[piece])
            if holding_pieces:
                if enable_bfen:
                    fenstr.append("/")
                    fenstr += holding_pieces
                else:
                    fenstr.append("[")
                    fenstr += holding_pieces
                    fenstr.append("]")

        fenstr.append(" ")

        fenstr.append(self.color == WHITE and "w" or "b")
        fenstr.append(" ")

        if self.variant == CAMBODIANCHESS:
            cast = ""
            if self.is_first_move[KING][WHITE]:
                cast += "D"
            if self.is_first_move[QUEEN][WHITE]:
                cast += "E"
            if self.is_first_move[KING][BLACK]:
                cast += "d"
            if self.is_first_move[QUEEN][BLACK]:
                cast += "e"
            if not cast:
                cast = "-"
            fenstr.append(cast)
        else:
            fenstr.append(self.reprCastling())
        fenstr.append(" ")

        if not self.enpassant:
            fenstr.append("-")
        else:
            fenstr.append(reprCord[self.enpassant])
        fenstr.append(" ")

        fenstr.append(str(self.fifty))
        fenstr.append(" ")

        fullmove = (self.plyCount) // 2 + 1
        fenstr.append(str(fullmove))

        return "".join(fenstr)

    def clone(self):
        copy = LBoard(self.variant)
        copy.blocker = self.blocker

        copy.friends = self.friends[:]
        copy.kings = self.kings[:]
        copy.boards = [self.boards[WHITE][:], self.boards[BLACK][:]]
        copy.arBoard = self.arBoard[:]
        copy.pieceCount = [self.pieceCount[WHITE][:],
                           self.pieceCount[BLACK][:]]

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
            copy.ini_rooks = (self.ini_rooks[0][:], self.ini_rooks[1][:])
        elif self.variant in (WILDCASTLECHESS, WILDCASTLESHUFFLECHESS):
            copy.ini_kings = self.ini_kings[:]
            copy.fin_kings = (self.fin_kings[0][:], self.fin_kings[1][:])
            copy.fin_rooks = (self.fin_rooks[0][:], self.fin_rooks[1][:])
        elif self.variant in DROP_VARIANTS:
            copy.promoted = self.promoted[:]
            copy.holding = (self.holding[0].copy(), self.holding[1].copy())
            copy.capture_promoting = self.capture_promoting
            copy.hist_capture_promoting = self.hist_capture_promoting[:]
        elif self.variant == ATOMICCHESS:
            copy.hist_exploding_around = [a[:]
                                          for a in self.hist_exploding_around]
        elif self.variant == CAMBODIANCHESS:
            copy.ini_kings = self.ini_kings
            copy.ini_queens = self.ini_queens
            copy.is_first_move = {KING: self.is_first_move[KING][:],
                                  QUEEN: self.is_first_move[QUEEN][:]}
            copy.hist_is_first_move = self.hist_is_first_move[:]

        copy.fen_was_applied = self.fen_was_applied
        return copy

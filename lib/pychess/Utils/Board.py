
from .lutils.bitboard import iterBits
from .lutils.LBoard import LBoard
from .lutils.lmove import RANK, FILE, FCORD, FLAG, PROMOTE_PIECE
from .Piece import Piece
from .Cord import Cord
from .const import A1, A8, B1, B8, C1, C8, D1, D8, E1, E8, F1, F8, G1, G8, H1, H8, \
    BISHOP, ROOK, ROOK_PROMOTION, QUEEN_PROMOTION, KNIGHT_PROMOTION, BLACK, FEN_START, \
    WHITE, NORMALCHESS, PAWN, BISHOP_PROMOTION, KNIGHT, QUEEN, KING, DROP_VARIANTS, NULL_MOVE, \
    DROP, ATOMICCHESS, ENPASSANT, FISCHERRANDOMCHESS, QUEEN_CASTLE, CRAZYHOUSECHESS, KING_CASTLE, \
    WILDCASTLECHESS, PROMOTIONS, WILDCASTLESHUFFLECHESS, SITTUYINCHESS, FAN_PIECES


def reverse_enum(L):
    for index in reversed(range(len(L))):
        yield index, L[index]


class Board:
    """ Board is a thin layer above LBoard, adding the Piece objects, which are
        needed for animation in BoardView.
        In contrast to LBoard, Board is immutable, which means it will clone
        itself each time you apply a move to it.
        Caveat: As the only objects, the Piece objects in the self.data lists
        will not be cloned, to make animation state preserve between moves """

    variant = NORMALCHESS
    RANKS = 8
    FILES = 8
    HOLDING_FILES = ((FILES + 3, FILES + 2, FILES + 1), (-4, -3, -2))
    PROMOTION_ZONE = ((A8, B8, C8, D8, E8, F8, G8, H8),
                      (A1, B1, C1, D1, E1, F1, G1, H1))
    PROMOTIONS = (QUEEN_PROMOTION, ROOK_PROMOTION, BISHOP_PROMOTION,
                  KNIGHT_PROMOTION)

    def __init__(self, setup=False, lboard=None):
        self.data = [dict(enumerate([None] * self.FILES))
                     for i in range(self.RANKS)]
        if lboard is None:
            self.board = LBoard(self.variant)
        else:
            self.board = lboard
        self.board.pieceBoard = self

        # Set True in interactive lesson games after they happened
        self.played = False

        if setup:
            if lboard is None:
                if setup is True:
                    self.board.applyFen(FEN_START)
                elif isinstance(setup, str):
                    self.board.applyFen(setup)

            for color in (BLACK, WHITE):
                pieces = self.board.boards[color]
                for piece in (PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING):
                    for cord in iterBits(pieces[piece]):
                        self.data[RANK(cord)][FILE(cord)] = Piece(color, piece)

            if self.variant in DROP_VARIANTS:
                for color in (BLACK, WHITE):
                    holding = self.board.holding[color]
                    for piece in holding:
                        for i in range(holding[piece]):
                            self[self.newHoldingCord(color, 1)] = Piece(color,
                                                                        piece)

    def getHoldingCord(self, color, piece):
        """Get the chord of first occurrence of piece in given color holding"""

        enum = reverse_enum if color == WHITE else enumerate
        for x_loc in self.HOLDING_FILES[color]:
            for y_loc, row in enum(self.data):
                if (row.get(x_loc) is not None) and row.get(x_loc).piece == piece:
                    return Cord(x_loc, y_loc)

    def newHoldingCord(self, color, nth=1):
        """Find the nth empty slot in given color holding.
        In atomic explosions nth can be > 1.
        """

        enum = reverse_enum if color == BLACK else enumerate
        empty = 0
        for x_loc in reversed(self.HOLDING_FILES[color]):
            for y_loc, row in enum(self.data):
                if row.get(x_loc) is None:
                    empty += 1
                    if empty == nth:
                        return Cord(x_loc, y_loc)

    def getHoldingPieces(self, color):
        """Get the list of pieces from given color holding"""
        pieces = []
        for x_loc in self.HOLDING_FILES[color]:
            for row in self.data:
                if row.get(x_loc) is not None:
                    pieces.append(row.get(x_loc))
        return pieces

    def popPieceFromHolding(self, color, piece):
        """Remove and return a piece in given color holding"""

        for x_loc in self.HOLDING_FILES[color]:
            for row in self.data:
                if (row.get(x_loc) is not None) and row.get(x_loc).piece == piece:
                    piece = row.get(x_loc)
                    del row[x_loc]
                    return piece
        return None

    def reorderHolding(self, color):
        """Reorder captured pieces by their value"""
        pieces = []
        for piece in (PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING):
            while True:
                col_piece = self.popPieceFromHolding(color, piece)
                if col_piece is not None:
                    pieces.append(col_piece)
                else:
                    break
        for piece in pieces:
            self[self.newHoldingCord(color, 1)] = piece

    def simulateMove(self, board1, move):
        moved = []
        new = []
        dead = []

        if move.flag == NULL_MOVE:
            return moved, new, dead

        cord0, cord1 = move.cords

        if cord0 == cord1 and self.variant == SITTUYINCHESS:
            return moved, new, dead

        if move.flag == DROP:
            piece = FCORD(move.move)
            cord0 = self.getHoldingCord(self.color, piece)
            moved.append((self[cord0], cord0))
            # add all captured pieces to "new" list to enforce repainting them after a possible reordering
            new = board1.getHoldingPieces(self.color)
            dead = new
            return moved, new, dead

        if self.variant == ATOMICCHESS and (self[cord1] or
                                            move.flag == ENPASSANT):
            # Sequence nubers of next newHoldingCord of WHITE and BLACK
            nth = [0, 0]

            piece = self[cord0]
            nth[1 - piece.color] += 1
            cord = self.newHoldingCord(1 - piece.color, nth[1 - piece.color])
            moved.append((board1[cord], cord0))
            new.append(board1[cord])
        else:
            if move.flag in PROMOTIONS:
                dead.append(self[cord0])
            else:
                moved.append((self[cord0], cord0))

        if self[cord1] and not (self.variant == FISCHERRANDOMCHESS and
                                move.flag in (QUEEN_CASTLE, KING_CASTLE)):
            piece = PAWN if self.variant == CRAZYHOUSECHESS and self[
                cord1].promoted else self[cord1].piece
            cord = board1.getHoldingCord(self.color, piece)
            moved.append((board1[cord], cord1))
            # add all captured pieces to "new" list to enforce repainting them after a possible reordering
            new = board1.getHoldingPieces(self.color)

            if self.variant == ATOMICCHESS:
                nth[self.color] += 1
                from pychess.Variants.atomic import cordsAround
                for acord in cordsAround(cord1):
                    piece = self[acord]
                    if piece and piece.piece != PAWN and acord != cord0:
                        nth[1 - piece.color] += 1
                        cord = self.newHoldingCord(1 - piece.color,
                                                   nth[1 - piece.color])
                        moved.append((board1[cord], acord))
                        new.append(board1[cord])

        if move.flag in (QUEEN_CASTLE, KING_CASTLE):
            side = move.flag - QUEEN_CASTLE
            if FILE(cord0.x) == 3 and self.board.variant in (
                    WILDCASTLECHESS, WILDCASTLESHUFFLECHESS):
                side = 0 if side == 1 else 1
            rook = self.board.ini_rooks[self.color][side]
            moved.append((self[Cord(rook)], Cord(rook)))

        elif move.flag in PROMOTIONS:
            newPiece = board1[cord1]
            moved.append((newPiece, cord0))
            new.append(newPiece)

        elif move.flag == ENPASSANT:
            shift = -1 if self.color == WHITE else 1
            ep_cord = Cord(cord1.x, cord1.y + shift)
            moved.append((self[ep_cord], ep_cord))
            # add all captured pieces to "new" list to enforce repainting them after a possible reordering
            new = board1.getHoldingPieces(self.color)

        return moved, new, dead

    def simulateUnmove(self, board1, move):
        moved = []
        new = []
        dead = []

        if move.flag == NULL_MOVE:
            return moved, new, dead

        cord0, cord1 = move.cords

        if cord0 == cord1 and self.variant == SITTUYINCHESS:
            return moved, new, dead

        if self.variant == ATOMICCHESS and (board1[cord1] or
                                            move.flag == ENPASSANT):
            piece = board1[cord0].piece
            cord = self.getHoldingCord(self.color, piece)
            moved.append((self[cord], cord))
            self[cord].opacity = 1
            dead.append(self[cord])
        elif not (self.variant == FISCHERRANDOMCHESS and move.flag in
                  (QUEEN_CASTLE, KING_CASTLE)):
            moved.append((self[cord1], cord1))

        if board1[cord1] and not (self.variant == FISCHERRANDOMCHESS and
                                  move.flag in (QUEEN_CASTLE, KING_CASTLE)):
            piece = PAWN if self.variant == CRAZYHOUSECHESS and board1[
                cord1].promoted else board1[cord1].piece
            cord = self.getHoldingCord(1 - self.color, piece)
            moved.append((self[cord], cord))
            self[cord].opacity = 1
            # add all captured pieces to "new" list to enforce repainting them after a possible reordering
            new = self.getHoldingPieces(self.color)
            dead.append(self[cord])

            if self.variant == ATOMICCHESS:
                from pychess.Variants.atomic import cordsAround
                for acord in cordsAround(cord1):
                    piece = board1[acord]
                    if piece and piece.piece != PAWN and acord != cord0:
                        piece.opacity = 0
                        cord = self.getHoldingCord(1 - piece.color,
                                                   piece.piece)
                        moved.append((self[cord], cord))
                        self[cord].opacity = 1
                        dead.append(self[cord])

        if move.flag in (QUEEN_CASTLE, KING_CASTLE):
            side = move.flag - QUEEN_CASTLE
            if FILE(cord0.x) == 3 and self.board.variant in (
                    WILDCASTLECHESS, WILDCASTLESHUFFLECHESS):
                side = 0 if side == 1 else 1
            rook = self.board.fin_rooks[board1.color][side]
            moved.append((self[Cord(rook)], Cord(rook)))

        elif move.flag in PROMOTIONS:
            newPiece = board1[cord0]
            moved.append((newPiece, cord1))
            new.append(newPiece)

        elif move.flag == ENPASSANT:
            cord = self.getHoldingCord(1 - self.color, PAWN)
            moved.append((self[cord], cord))
            self[cord].opacity = 1
            # add all captured pieces to "new" list to enforce repainting them after a possible reordering
            new = self.getHoldingPieces(self.color)
            dead.append(self[cord])

        return moved, new, dead

    def move(self, move, lboard=None):
        """ Creates a new Board object cloning itself then applying
            the move.move to the clone Board's lboard.
            If lboard param was given, it will be used when cloning,
            and move will not be applyed, just the high level Piece
            objects will be adjusted."""

        # Sequence nubers of next newHoldingCord of WHITE and BLACK
        nth = [0, 0]

        flag = FLAG(move.move)
        if flag != DROP:
            assert self[move.cord0], "%s %s" % (move, self.asFen())

        newBoard = self.clone(lboard=lboard)
        if lboard is None:
            newBoard.board.applyMove(move.move)

        cord0, cord1 = move.cords

        if (self[move.cord1] is not None or flag == ENPASSANT) and \
                not (cord0 == cord1 and self.variant == SITTUYINCHESS) and \
                not (flag in (QUEEN_CASTLE, KING_CASTLE)):
            if self.variant == CRAZYHOUSECHESS:
                piece = PAWN if flag == ENPASSANT or self[
                    move.cord1].promoted else self[move.cord1].piece
                new_piece = Piece(self.color, piece, captured=True)
            else:
                piece = PAWN if flag == ENPASSANT else self[move.cord1].piece
                new_piece = Piece(1 - self.color, piece, captured=True)
            nth[self.color] += 1
            newBoard[self.newHoldingCord(self.color, nth[
                self.color])] = new_piece

            if self.variant == ATOMICCHESS:
                from pychess.Variants.atomic import cordsAround
                for acord in cordsAround(move.cord1):
                    piece = self[acord]
                    if piece and piece.piece != PAWN and acord != cord0:
                        new_piece = Piece(piece.color,
                                          piece.piece,
                                          captured=True)
                        nth[1 - piece.color] += 1
                        newBoard[self.newHoldingCord(1 - piece.color, nth[
                            1 - piece.color])] = new_piece
                        newBoard[acord] = None

        if flag == DROP:
            piece = FCORD(move.move)
            holding_coord = self.getHoldingCord(self.color, piece)
            if holding_coord is None:
                newBoard[cord1] = Piece(self.color, piece)
            else:
                newBoard[cord1] = newBoard[holding_coord]
                newBoard[cord1].captured = False
                newBoard[holding_coord] = None
        else:
            if self.variant == ATOMICCHESS and (
                flag == ENPASSANT or self[move.cord1] is not None) and (
                    flag not in (QUEEN_CASTLE, KING_CASTLE)):
                piece = self[move.cord0].piece
                new_piece = Piece(self.color, piece, captured=True)
                nth[1 - self.color] += 1
                newBoard[self.newHoldingCord(1 - self.color, nth[
                    1 - self.color])] = new_piece
                newBoard[cord1] = None
            else:
                if flag in (QUEEN_CASTLE, KING_CASTLE):
                    king = newBoard[cord0]
                else:
                    newBoard[cord1] = newBoard[cord0]

        if flag != NULL_MOVE and flag != DROP:
            newBoard[cord0] = None

        if flag in (QUEEN_CASTLE, KING_CASTLE):
            side = flag - QUEEN_CASTLE
            if FILE(cord0.x) == 3 and self.board.variant in (
                    WILDCASTLECHESS, WILDCASTLESHUFFLECHESS):
                side = 0 if side == 1 else 1
            inirook = self.board.ini_rooks[self.color][side]
            finrook = self.board.fin_rooks[self.color][side]
            newBoard[Cord(finrook)] = newBoard[Cord(inirook)]
            if inirook != finrook:
                newBoard[Cord(inirook)] = None
            finking = self.board.fin_kings[self.color][side]
            newBoard[Cord(finking)] = king

        if flag in PROMOTIONS:
            new_piece = Piece(self.color, PROMOTE_PIECE(flag))
            new_piece.promoted = True
            newBoard[cord1] = new_piece

        elif flag == ENPASSANT:
            newBoard[Cord(cord1.x, cord0.y)] = None

        if flag == DROP or flag == ENPASSANT or self[move.cord1] is not None:
            newBoard.reorderHolding(self.color)
        return newBoard

    def switchColor(self):
        """ Switches the current color to move and unsets the enpassant cord.
            Mostly to be used by inversed analyzers """
        new_board = self.setColor(1 - self.color)
        new_board.board.next = self.board.next
        return new_board

    def _get_enpassant(self):
        if self.board.enpassant is not None:
            return Cord(self.board.enpassant)
        return None

    enpassant = property(_get_enpassant)

    def setColor(self, color):
        newBoard = self.clone()
        newBoard.board.setColor(color)
        newBoard.board.setEnpassant(None)
        return newBoard

    def _get_color(self):
        return self.board.color

    color = property(_get_color)

    def _get_ply(self):
        return self.board.plyCount

    ply = property(_get_ply)

    def asFen(self, enable_bfen=True):
        return self.board.asFen(enable_bfen)

    def __repr__(self):
        return repr(self.board)

    def __getitem__(self, cord):
        return self.data[cord.y].get(cord.x)

    def __setitem__(self, cord, piece):
        self.data[cord.y][cord.x] = piece

    def clone(self, lboard=None):
        if lboard is None:
            lboard = self.board.clone()

        if self.variant != NORMALCHESS:
            from pychess.Variants import variants
            newBoard = variants[self.variant]()
        else:
            newBoard = Board()
        newBoard.board = lboard
        newBoard.board.pieceBoard = newBoard

        for y, row in enumerate(self.data):
            for x, piece in row.items():
                newBoard.data[y][x] = piece

        return newBoard

    def __eq__(self, other):
        if not isinstance(self, type(other)):
            return False
        return self.board == other.board

    def printPieces(self):
        board = ""
        for row in reversed(self.data):
            for i in range(-3, 11):
                piece = row.get(i)
                if piece is not None:
                    if piece.color == BLACK:
                        piece_colour = FAN_PIECES[BLACK][piece.piece]
                    else:
                        piece_colour = FAN_PIECES[WHITE][piece.piece]
                    board += piece_colour
                else:
                    board += '.'
            board += "\n"
        print(board)

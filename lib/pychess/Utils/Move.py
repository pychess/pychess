from pychess.Utils.Cord import Cord
from pychess.Utils.const import (
    DROP,
    NORMAL_MOVE,
    PAWN,
    SITTUYINCHESS,
    QUEEN,
    KING,
    WHITE,
    BLACK,
    W_OOO,
    W_OO,
    B_OOO,
    B_OO,
    QUEEN_CASTLE,
    FISCHERRANDOMCHESS,
    GATINGS,
    KING_CASTLE,
    CAMBODIANCHESS,
    ENPASSANT,
    PROMOTIONS,
    CASTLE_SAN,
    C1,
    G1,
    reprSign,
    LIGHTBRIGADECHESS,
    KNIGHT,
)
from pychess.Utils.lutils.lmovegen import newMove
from .lutils import lmove


class Move:
    def __init__(self, cord0, cord1=None, board=None, promotion=None):
        """Inits a new highlevel Move object.
        The object can be initialized in the follow ways:
            Move(cord0, cord1, board, [promotionPiece])
            Move(lovLevelMoveInt)"""

        if not cord1:
            self.move = cord0
            self.flag = self.move >> 12
            self.cord0 = None if self.flag == DROP else Cord(lmove.FCORD(self.move))
            self.cord1 = Cord(lmove.TCORD(self.move))
        else:
            assert (
                cord0 is not None and cord1 is not None
            ), f"cord0={cord0}, cord1={cord1}, board={board}"
            assert board[cord0] is not None, "cord0={}, cord1={}, board={}".format(
                cord0, cord1, board
            )
            self.cord0 = cord0
            self.cord1 = cord1
            if not board:
                raise ValueError(
                    "Move needs a Board object in order to investigate flags"
                )

            self.flag = NORMAL_MOVE
            if (
                board[self.cord0].piece == PAWN
                and self.cord1.cord in board.PROMOTION_ZONE[board.board.color]
                and board.variant != SITTUYINCHESS
            ):
                if promotion is None:
                    if board.variant == LIGHTBRIGADECHESS:
                        self.flag = lmove.FLAG_PIECE(
                            QUEEN if board.board.color == WHITE else KNIGHT
                        )
                    else:
                        self.flag = lmove.FLAG_PIECE(QUEEN)
                else:
                    self.flag = lmove.FLAG_PIECE(promotion)

            elif board[self.cord0].piece == PAWN and board.variant == SITTUYINCHESS:
                if cord0 == cord1:
                    # in place promotion
                    self.flag = lmove.FLAG_PIECE(QUEEN)
                elif (
                    board[self.cord1] is None
                    and (self.cord0.cord + self.cord1.cord) % 2 == 1
                    and (
                        self.cord0.cord in board.PROMOTION_ZONE[board.board.color]
                        or board.board.pieceCount[board.color][PAWN] == 1
                    )
                ):
                    # queen move promotion
                    self.flag = lmove.FLAG_PIECE(QUEEN)

            elif board[self.cord0].piece == KING:
                if self.cord0.x - self.cord1.x == 2 and board.variant not in (
                    CAMBODIANCHESS,
                    FISCHERRANDOMCHESS,
                ):
                    self.flag = QUEEN_CASTLE if self.cord0.x == 4 else KING_CASTLE
                elif self.cord0.x - self.cord1.x == -2 and board.variant not in (
                    CAMBODIANCHESS,
                    FISCHERRANDOMCHESS,
                ):
                    self.flag = KING_CASTLE if self.cord0.x == 4 else QUEEN_CASTLE
                elif board.variant != CAMBODIANCHESS:
                    if (
                        abs(self.cord0.x - self.cord1.x) > 1 and self.cord1.x == C1
                    ) or (
                        board.board.ini_rooks[board.color][0] == self.cord1.cord
                        and (
                            (
                                board.board.color == WHITE
                                and board.board.castling & W_OOO
                            )
                            or (
                                board.board.color == BLACK
                                and board.board.castling & B_OOO
                            )
                        )
                    ):
                        self.flag = QUEEN_CASTLE
                    elif (
                        abs(self.cord0.x - self.cord1.x) > 1 and self.cord1.x == G1
                    ) or (
                        board.board.ini_rooks[board.color][1] == self.cord1.cord
                        and (
                            (board.board.color == WHITE and board.board.castling & W_OO)
                            or (
                                board.board.color == BLACK
                                and board.board.castling & B_OO
                            )
                        )
                    ):
                        self.flag = KING_CASTLE
            elif (
                board[self.cord0].piece == PAWN
                and board[self.cord1] is None
                and self.cord0.x != self.cord1.x
                and self.cord0.y != self.cord1.y
            ):
                self.flag = ENPASSANT

            self.move = newMove(self.cord0.cord, self.cord1.cord, self.flag)

    def _get_cords(self):
        return (self.cord0, self.cord1)

    cords = property(_get_cords)

    def _get_promotion(self):
        if self.flag in PROMOTIONS:
            return lmove.PROMOTE_PIECE(self.flag)
        return None

    promotion = property(_get_promotion)

    def __repr__(self):
        promotion = (
            "=" + reprSign[lmove.PROMOTE_PIECE(self.flag)]
            if self.flag in PROMOTIONS
            else ""
        )

        gate_piece = (
            reprSign[lmove.GATE_PIECE(self.flag)].lower()
            if self.flag in GATINGS
            else ""
        )
        if self.flag == DROP:
            piece = reprSign[lmove.FCORD(self.move)]
            return piece + "@" + str(self.cord1) + promotion
        else:
            return str(self.cord0) + str(self.cord1) + gate_piece + promotion

    def __eq__(self, other):
        if isinstance(other, Move):
            return self.move == other.move

    def __hash__(self):
        return hash(self.cords)

    def is_capture(self, board):
        return (
            self.flag == ENPASSANT
            or board[self.cord1] is not None
            and self.flag != QUEEN_CASTLE
            and self.flag != KING_CASTLE
        )

    def as_uci(self):
        move = "{}{}{}{}".format(
            self.cord0.cx, self.cord0.cy, self.cord1.cx, self.cord1.cy
        )
        if self.flag in PROMOTIONS:
            move += reprSign[lmove.PROMOTE_PIECE(self.flag)].lower()
        return move


# Parsers


def listToMoves(board, mstrs, type=None, validate=False, ignoreErrors=False):
    return [
        Move(move)
        for move in lmove.listToMoves(board.board, mstrs, type, validate, ignoreErrors)
    ]


def parseAny(board, algnot):
    return Move(lmove.parseAny(board.board, algnot))


def parseSAN(board, san):
    """Parse a Short/Abbreviated Algebraic Notation string"""

    return Move(lmove.parseSAN(board.board, san))


def parseLAN(board, lan):
    """Parse a Long/Expanded Algebraic Notation string"""

    return Move(lmove.parseLAN(board.board, lan))


def parseFAN(board, lan):
    """Parse a Long/Expanded Algebraic Notation string"""

    return Move(lmove.parseFAN(board.board, lan))


def parseAN(board, an):
    """Parse an Algebraic Notation string"""

    return Move(lmove.parseAN(board.board, an))


# Exporters


def listToSan(board, moves):
    return lmove.listToSan(board.board, (m.move for m in moves))


def toAN(board, move, short=False, castleNotation=CASTLE_SAN):
    """Returns a Algebraic Notation string of a move
    board should be prior to the move"""

    return lmove.toAN(
        board.board, move.move, short=short, castleNotation=castleNotation
    )


def toSAN(board, move, localRepr=False):
    """Returns a Short/Abbreviated Algebraic Notation string of a move
    The board should be prior to the move, board2 past.
    If not board2, toSAN will not test mate"""

    return lmove.toSAN(board.board, move.move, localRepr)


def toLAN(board, move):
    """Returns a Long/Expanded Algebraic Notation string of a move
    board should be prior to the move"""

    return lmove.toLAN(board.board, move.move)


def toFAN(board, move):
    """Returns a Figurine Algebraic Notation string of a move"""

    return lmove.toFAN(board.board, move.move)

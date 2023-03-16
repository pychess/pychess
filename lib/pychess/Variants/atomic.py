# Atomic Chess

from pychess.Utils.const import (
    VARIANTS_OTHER_NONSTANDARD,
    KING,
    ATOMICCHESS,
    ENPASSANT,
    B8,
    E1,
)
from pychess.Utils.Board import Board
from pychess.Utils.Cord import Cord
from pychess.Utils.Move import Move
from pychess.Utils.lutils.bitboard import iterBits
from pychess.Utils.lutils.ldata import moveArray


class AtomicBoard(Board):
    variant = ATOMICCHESS
    __desc__ = _("FICS atomic: http://www.freechess.org/Help/HelpFiles/atomic.html")
    name = _("Atomic")
    cecp_name = "atomic"
    need_initial_board = False
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD


def cordsAround(cord):
    kingMoves = moveArray[KING]
    for co_ord in iterBits(kingMoves[cord.cord]):
        yield Cord(co_ord)


def piecesAround(board, cord):
    kingMoves = moveArray[KING]

    friends = board.friends[board.color]
    for co_ord in iterBits(kingMoves[cord] & friends):
        yield co_ord, board.arBoard[co_ord], board.color

    enemies = board.friends[1 - board.color]
    for co_ord in iterBits(kingMoves[cord] & enemies):
        yield co_ord, board.arBoard[co_ord], 1 - board.color


def kingExplode(board, move, color):
    tcord = move & 63
    # fcord = (move >> 6) & 63
    flag = move >> 12
    if board.arBoard[tcord] or flag == ENPASSANT:
        for acord, apiece, acolor in piecesAround(board, tcord):
            if apiece == KING and acolor == color:
                return True
    return False


if __name__ == "__main__":
    FEN = "rnbqkbnr/ppp1pppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1"
    atomic_board = AtomicBoard(FEN)
    print(atomic_board.board.__repr__())

    for acord, apiece, acolor in piecesAround(atomic_board.board, B8):
        print(acord, apiece, acolor)
    for acord, apiece, acolor in piecesAround(atomic_board.board, E1):
        print(acord, apiece, acolor)

    from pychess.Utils.lutils.lmove import parseAN

    atomic_board = atomic_board.move(Move(parseAN(atomic_board.board, "d8d2")))
    print(atomic_board.board.__repr__())
    print(atomic_board.board.pieceCount)

    atomic_board.board.popMove()
    print(atomic_board.board.__repr__())
    print(atomic_board.board.pieceCount)

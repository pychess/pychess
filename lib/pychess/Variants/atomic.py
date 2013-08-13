# Atomic Chess

from pychess.Utils.const import *
from pychess.Utils.Board import Board
from pychess.Utils.Cord import Cord
from pychess.Utils.Move import Move
from pychess.Utils.lutils.bitboard import *
from pychess.Utils.lutils.ldata import *


class AtomicBoard(Board):
    variant = ATOMICCHESS

class AtomicChess:
    __desc__ = _("FICS atomic: http://www.freechess.org/Help/HelpFiles/atomic.html")
    name = _("Atomic")
    cecp_name = "atomic"
    board = AtomicBoard
    need_initial_board = False
    standard_rules = False
    variant_group = VARIANTS_OTHER

offsets = (-9, -8, -7, -1, 1, 7, 8, 9)
def cordsAround(cord):
    for offset in offsets:
        c = cord.cord+offset
        if c >=0 and c<64:
            yield Cord(c)
    
def piecesAround(board, cord):
    kingMoves = moveArray[KING]

    friends = board.friends[board.color]
    for c in iterBits(kingMoves[cord] & friends):
        yield c, board.arBoard[c], board.color

    enemies = board.friends[1- board.color]
    for c in iterBits(kingMoves[cord] & enemies):
        yield c, board.arBoard[c], 1-board.color

def kingExplode(board, move, color):
    tcord = move & 63
    fcord = (move >> 6) & 63
    if board.arBoard[tcord] and board.arBoard[fcord] != KING:
        for acord, apiece, acolor in piecesAround(board, tcord):
            if apiece == KING and acolor == color and acord != fcord:
                return True
    return False

if __name__ == '__main__':
    FEN = "rnbqkbnr/ppp1pppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1"
    b = AtomicBoard(FEN)
    print b.board.__repr__()
    
    for acord, apiece, acolor in piecesAround(b.board, B8):
        print acord, apiece, acolor
    for acord, apiece, acolor in piecesAround(b.board, E1):
        print acord, apiece, acolor
    
    from pychess.Utils.lutils.lmove import parseAN
    b = b.move(Move(parseAN(b.board, "d8d2")))
    print b.board.__repr__()
    print b.board.pieceCount

    b.board.popMove()
    print b.board.__repr__()
    print b.board.pieceCount
    

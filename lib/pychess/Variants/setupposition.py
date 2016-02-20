from pychess.Utils.const import SETUPCHESS, VARIANTS_OTHER, BLACK, reprSign
from pychess.Utils.Board import Board
from pychess.Utils.Piece import Piece

SETUPSTART = "4k3/8/8/8/8/8/8/4K3 w - - 0 1"


class SetupBoard(Board):
    variant = SETUPCHESS
    __desc__ = ""
    name = ""
    cecp_name = ""
    standard_rules = False
    variant_group = VARIANTS_OTHER

    PROMOTION_ZONE = ((), ())
    PROMOTIONS = ()

    def __init__(self, setup=True):
        fenstr = SETUPSTART if setup is True else setup
        # add all kind if piece to holdings (except king)
        parts = fenstr.split()
        parts[0] += "/prnsqPRNSQ"
        fenstr = " ".join(parts)
        Board.__init__(self, setup=fenstr)
        self._ply = 0

    def _get_ply(self):
        return self._ply

    ply = property(_get_ply)

    def simulateMove(self, board, move):
        moved = []
        new = []
        dead = []

        cord0, cord1 = move.cord0, move.cord1
        if cord1.x < 0 or cord1.x > self.FILES - 1:
            dead.append(self[cord0])
        else:
            moved.append((self[cord0], cord0))

        return moved, new, dead

    def move(self, move, color):
        new_board = self.clone()
        new_board._ply = self._ply + 1
        cord0, cord1 = move.cord0, move.cord1
        if cord0.x < 0 or cord0.x > self.FILES - 1 and \
                (cord1.x >= 0 and cord1.x <= 7):
            new_board[cord1] = new_board[cord0]
            new_board[cord0] = Piece(color, self[cord0].sign)
        elif cord1.x < 0 or cord1.x > self.FILES - 1:
            new_board[cord0] = None
        else:
            new_board[cord1] = new_board[cord0]
            new_board[cord0] = None
        return new_board

    def as_fen(self):
        fenstr = []
        for r, row in enumerate(reversed(self.data)):
            empty = 0
            for i in range(0, 8):
                piece = row.get(i)
                if piece is not None:
                    if empty > 0:
                        fenstr.append(str(empty))
                        empty = 0
                    sign = reprSign[piece.piece]
                    if piece.color == BLACK:
                        sign = sign.lower()
                    else:
                        sign = sign.upper()
                    fenstr.append(sign)
                else:
                    empty += 1
            if empty > 0:
                fenstr.append(str(empty))
            if r != 7:
                fenstr.append("/")
        return "".join(fenstr)

    def __repr__(self):
        return self.as_fen()

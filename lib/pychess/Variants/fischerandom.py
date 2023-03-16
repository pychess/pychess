# Chess960 (Fischer Random Chess)

from random import randrange
from math import floor

from pychess.Utils.const import FISCHERRANDOMCHESS, VARIANTS_SHUFFLE
from pychess.Utils.Board import Board
from pychess.Utils.const import reprFile


class FischerandomBoard(Board):
    variant = FISCHERRANDOMCHESS
    __desc__ = _(
        "http://en.wikipedia.org/wiki/Chess960\n"
        + "FICS wild/fr: http://www.freechess.org/Help/HelpFiles/wild.html"
    )
    name = _("Fischer Random")
    cecp_name = "fischerandom"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_SHUFFLE

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=self.shuffle_start(), lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

    def getFrcFen(self, position=519):
        position = max(1, min(960, position))
        pieces = ["", "", "", "", "", "", "", ""]

        # Bishops
        pieces[floor(0.08 * (floor(25 * (position - 1)) % 100) + 1.5)] = "b"
        pieces[floor(0.08 * (floor(25 * floor((position - 1) / 4)) % 100) + 0.5)] = "b"

        # Queen
        z = floor(floor((position - 1) / 4) / 4) / 6
        p = floor(6 * (z - floor(z)) + 0.5)
        for i in range(8):
            if pieces[i] == "":
                if p == 0:
                    pieces[i] = "q"
                    break
                p -= 1

        # KRN
        krn = [
            "nnrkr",
            "nrnkr",
            "nrknr",
            "nrkrn",
            "rnnkr",
            "rnknr",
            "rnkrn",
            "rknnr",
            "rknrn",
            "rkrnn",
        ][floor(z)]
        for i in range(8):
            if pieces[i] == "":
                pieces[i] = krn[:1]
                krn = krn[1:]

        # Castling
        castling = ""
        for i in range(8):
            if pieces[i] == "r":
                castling += reprFile[i]

        # FEN
        pieces = "".join(pieces)
        return "{}/pppppppp/8/8/8/8/PPPPPPPP/{} w {}{} - 0 1".format(
            pieces, pieces.upper(), castling.upper(), castling
        )

    def shuffle_start(self):
        return self.getFrcFen(randrange(1, 960))


if __name__ == "__main__":
    frcBoard = FischerandomBoard(True)
    for i in range(10):
        print(frcBoard.shuffle_start())

import unittest
from time import time

from pychess.Variants.losers import LosersBoard
from pychess.Utils.lutils import lsearch

# ♜ ♞ ♝ ♛ ♚ . ♞ ♜
# ♟ . ♟ . . ♟ ♟ ♟
# . ♟ . . ♟ . . .
# . . . ♟ ♙ . . .
# . ♝ . ♙ . . . .
# . . ♘ . . . . .
# ♙ ♙ ♙ . . ♙ ♙ ♙
# ♖ . ♗ ♕ ♔ ♗ ♘ ♖
FEN0 = "rnbqk1nr/p1p2ppp/1p2p3/3pP3/1b1P4/2N5/PPP2PPP/R1BQKBNR w KQkq - 0 5"


class alphabetaTests(unittest.TestCase):
    def test1(self):
        """Testing lsearch.alphaBeta() Losers variant"""

        board = LosersBoard(setup=FEN0)

        lsearch.searching = True
        lsearch.timecheck_counter = lsearch.TIMECHECK_FREQ
        lsearch.endtime = time() + 1

        mvs, scr = lsearch.alphaBeta(board.board, 1)

        self.assertNotEqual(mvs, [])


if __name__ == "__main__":
    unittest.main()

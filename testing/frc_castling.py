from __future__ import print_function
import unittest

from pychess.Utils.const import *
from pychess.Utils.lutils.leval import LBoard
from pychess.Utils.lutils.lmove import FLAG
from pychess.Utils.lutils.lmovegen import genCastles, newMove

# TODO: add more test data
data = (
 ("r3k2r/8/8/8/8/8/8/R3K2R w AH - 0 1", [(E1, H1, KING_CASTLE), (E1, A1, QUEEN_CASTLE)]),
 ("r3k2r/8/8/8/8/8/8/R3K2R b ah - 0 1", [(E8, H8, KING_CASTLE), (E8, A8, QUEEN_CASTLE)]),
 ("1br3kr/2p5/8/8/8/8/8/1BR3KR w CH - 0 2", [(G1, H1, KING_CASTLE), (G1, C1, QUEEN_CASTLE)]),
 ("1br3kr/2p5/8/8/8/8/8/1BR3KR b ch - 0 2", [(G8, H8, KING_CASTLE), (G8, C8, QUEEN_CASTLE)]),
 ("2r1k2r/8/8/8/8/8/8/2R1K2R w H - 0 1", [(E1, H1, KING_CASTLE)]),
 ("2r1k2r/8/8/8/8/8/8/2R1K2R b h - 0 1", [(E8, H8, KING_CASTLE)]),
 ("3rk1qr/8/8/8/8/8/8/3RK1QR w - - 0 1", []),
 ("3rk1qr/8/8/8/8/8/8/3RK1QR b - - 0 1", []),
 )

class FRCCastlingTestCase(unittest.TestCase):

    def testFRCCastling(self):
        """Testing FRC castling movegen"""
        print()

        for fen, castles in data:
            print(fen)
            board = LBoard(FISCHERRANDOMCHESS)
            board.applyFen(fen)
            #print board
            moves = [move for move in genCastles(board)]
            self.assertEqual(len(moves), len(castles))
            for i, castle in enumerate(castles):
                kfrom, kto, flag = castle
                self.assertEqual(moves[i], newMove(kfrom, kto, flag))


if __name__ == '__main__':
    unittest.main()

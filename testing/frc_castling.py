import unittest

from pychess.Utils.const import A1, A8, C1, C8, E1, E8, G1, G8, H1, H8,\
    FISCHERRANDOMCHESS, KING_CASTLE, QUEEN_CASTLE
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import parseAN
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
    ("3rk1qr/8/8/8/8/8/8/3RK1QR b - - 0 1", []),)


class FRCCastlingTestCase(unittest.TestCase):

    def testFRCCastling(self):
        """Testing FRC castling movegen"""
        print()

        for fen, castles in data:
            print(fen)
            board = LBoard(FISCHERRANDOMCHESS)
            board.applyFen(fen)
            # print board
            moves = [move for move in genCastles(board)]
            self.assertEqual(len(moves), len(castles))
            for i, castle in enumerate(castles):
                kfrom, kto, flag = castle
                self.assertEqual(moves[i], newMove(kfrom, kto, flag))

    def testFRCCastlingUCI(self):
        """Testing UCI engine FRC castling move"""
        print()

        fen = "rbq1krb1/pp1pp1pp/2p1n3/5p2/2PP1P1n/4B1N1/PP2P1PP/RBQNKR2 w FAfa - 2 6"
        print(fen)
        board = LBoard(FISCHERRANDOMCHESS)
        board.applyFen(fen)
        # print board
        moves = [move for move in genCastles(board)]
        self.assertTrue(parseAN(board, "e1g1") in moves)

if __name__ == '__main__':
    unittest.main()

import unittest

from pychess.Utils.const import GIVEAWAYCHESS, G1, G2, H2
from pychess.Utils.Move import Move
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import parseAN, parseSAN, parseFAN, toFAN, toSAN, ParsingError
from pychess.Utils.lutils.lmovegen import genAllMoves, newMove


class MoveTestCase(unittest.TestCase):
    def test_paresSAN1(self):
        """Testing parseSAN with unambiguous notations variants"""

        board = LBoard()
        board.applyFen("4k2B/8/8/8/8/8/8/B3K3 w - - 0 1")

        self.assertEqual(repr(Move(parseSAN(board, 'Ba1b2'))), 'a1b2')
        self.assertEqual(repr(Move(parseSAN(board, 'Bh8b2'))), 'h8b2')

        self.assertEqual(repr(Move(parseSAN(board, 'Bab2'))), 'a1b2')
        self.assertEqual(repr(Move(parseSAN(board, 'Bhb2'))), 'h8b2')

        self.assertEqual(repr(Move(parseSAN(board, 'B1b2'))), 'a1b2')
        self.assertEqual(repr(Move(parseSAN(board, 'B8b2'))), 'h8b2')

        board = LBoard()
        board.applyFen("4k2B/8/8/8/8/8/1b6/B3K3 w - - 0 1")

        self.assertEqual(repr(Move(parseSAN(board, 'Ba1xb2'))), 'a1b2')
        self.assertEqual(repr(Move(parseSAN(board, 'Bh8xb2'))), 'h8b2')

        self.assertEqual(repr(Move(parseSAN(board, 'Baxb2'))), 'a1b2')
        self.assertEqual(repr(Move(parseSAN(board, 'Bhxb2'))), 'h8b2')

        self.assertEqual(repr(Move(parseSAN(board, 'B1xb2'))), 'a1b2')
        self.assertEqual(repr(Move(parseSAN(board, 'B8xb2'))), 'h8b2')

    def test_paresSAN2(self):
        """Testing parseAN and parseSAN with bad promotions moves"""

        board = LBoard()
        board.applyFen("4k3/P7/8/8/8/8/8/4K3 w - - 0 1")

        self.assertRaises(ParsingError, parseAN, board, 'a7a8K')
        # If promotion piece is missing pychess assumes queen promotion from 0.99.2
        # self.assertRaises(ParsingError, parseAN, board, 'a7a8')

        self.assertRaises(ParsingError, parseSAN, board, 'a8K')
        # If promotion piece is missing pychess assumes queen promotion from 0.99.2
        # self.assertRaises(ParsingError, parseSAN, board, 'a8')

    def test_parseFAN(self):
        """Testing parseFAN"""

        board = LBoard()
        board.applyFen("rnbqkbnr/8/8/8/8/8/8/RNBQKBNR w KQkq - 0 1")

        for lmove in genAllMoves(board):
            board.applyMove(lmove)
            if board.opIsChecked():
                board.popMove()
                continue

            board.popMove()

            fan = toFAN(board, lmove)
            self.assertEqual(parseFAN(board, fan), lmove)

    def test_toSAN(self):
        """ Testing toSAN() with giveaway king move """

        board = LBoard(GIVEAWAYCHESS)
        board.applyFen("4R3/8/7B/2P5/8/8/PP5k/6k1 b - - 0 28")

        self.assertEqual(toSAN(board, newMove(G1, G2)), "Kgg2")
        self.assertEqual(toSAN(board, newMove(H2, G2)), "Khg2")


if __name__ == '__main__':
    unittest.main()

import sys
import unittest

from pychess.Utils.Move import Move
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import parseAN, parseSAN, parseFAN, toFAN, ParsingError
from pychess.Utils.lutils.lmovegen import genAllMoves


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
        self.assertRaises(ParsingError, parseAN, board, 'a7a8')

        self.assertRaises(ParsingError, parseSAN, board, 'a8K')
        self.assertRaises(ParsingError, parseSAN, board, 'a8')

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


if __name__ == '__main__':
    unittest.main()

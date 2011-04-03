import sys
import unittest

from pychess.Utils.Board import Board
from pychess.Utils.Move import parseSAN


class MoveTestCase(unittest.TestCase):
    
    def setUp(self):
        self.board = Board()

    def test_paresSAN(self):
        """Testing parseSAN with unambiguous notations variants"""
        
        self.board.board.applyFen("7B/8/8/8/8/8/8/B7 w - - 0 1")        

        self.assertEqual(repr(parseSAN(self.board, 'Ba1b2')), 'a1b2')
        self.assertEqual(repr(parseSAN(self.board, 'Bh8b2')), 'h8b2')

        self.assertEqual(repr(parseSAN(self.board, 'Bab2')), 'a1b2')
        self.assertEqual(repr(parseSAN(self.board, 'Bhb2')), 'h8b2')

        self.assertEqual(repr(parseSAN(self.board, 'B1b2')), 'a1b2')
        self.assertEqual(repr(parseSAN(self.board, 'B8b2')), 'h8b2')


        self.board.board.applyFen("7B/8/8/8/8/8/1b6/B7 w - - 0 1")        

        self.assertEqual(repr(parseSAN(self.board, 'Ba1xb2')), 'a1b2')
        self.assertEqual(repr(parseSAN(self.board, 'Bh8xb2')), 'h8b2')

        self.assertEqual(repr(parseSAN(self.board, 'Baxb2')), 'a1b2')
        self.assertEqual(repr(parseSAN(self.board, 'Bhxb2')), 'h8b2')

        self.assertEqual(repr(parseSAN(self.board, 'B1xb2')), 'a1b2')
        self.assertEqual(repr(parseSAN(self.board, 'B8xb2')), 'h8b2')


if __name__ == '__main__':
    unittest.main()

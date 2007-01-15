import unittest

import __builtin__
__builtin__.__dict__['_'] = lambda s: s

from pychess.Savers.epd import load
from pychess.Utils.validator import findMoves2 


class FindMovesTestCase(unittest.TestCase):
    """Move generator test using perftsuite.epd from
       http://www.albert.nu/programs/sharper/perft.htm"""

    def perft(self, board, depth):
        if depth == 0:
            self.count += 1
            return
        for move in findMoves2(board):
            self.perft(board.move(move), depth-1)

    def setUp(self):
        f = open('gamefiles/perftsuite.epd')
        epd = load(f)
        self.board = epd.loadToHistory(1, 0)[0]
 
    def testPerft_1(self):
        """Testing move generator with depth 1"""
        self.count = 0
        self.perft(self.board, 1)
        self.assertEqual(self.count, 48)

    def testPerft_2(self):
        """Testing move generator with depth 2"""
        self.count = 0
        self.perft(self.board, 2)
        self.assertEqual(self.count, 2039)

    def testPerft_3(self):
        """Testing move generator with depth 3 (this takes some minutes!)"""
        self.count = 0
        self.perft(self.board, 3)
        self.assertEqual(self.count, 97862)

if __name__ == '__main__':
    unittest.main()

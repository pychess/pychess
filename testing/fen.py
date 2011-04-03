import unittest

from pychess.Utils.Board import Board
from pychess.Utils.lutils.LBoard import LBoard
import sys


class FenTestCase(unittest.TestCase):
    
    def setUp(self):
        self.positions = []
        for line in open('gamefiles/perftsuite.epd'):
            semi = line.find(" ;")
            self.positions.append(line[:semi])
    
    def testFEN(self):
        """Testing board-FEN conversion with several positions"""
        print
        board = LBoard(Board)
        for i, fenstr in enumerate(self.positions[1:]):
            sys.stdout.write("#")
            board.applyFen(fenstr)
            fenstr2 = board.asFen()
            self.assertEqual(fenstr, fenstr2)
        print
            
if __name__ == '__main__':
    unittest.main()

import unittest

import __builtin__
__builtin__.__dict__['_'] = lambda s: s

from pychess.Savers.epd import load
from pychess.Utils.validator import findMoves2, validate


class FindMovesTestCase(unittest.TestCase):
    """Move generator test using perftsuite.epd from
       http://www.albert.nu/programs/sharper/perft.htm"""
    
    testDepth = 2
    
    def perft(self, board, depth):
        if depth == 0:
            self.count += 1
            return
        for move in findMoves2(board):
            # use this only if test failes
            #print move
            #if not validate(move, board):
                #print board, move
                #return
            self.perft(board.move(move), depth-1)

    def setUp(self):
        f = open('gamefiles/perftsuite.epd')
        data = f.readlines()
        f.seek(0)
        self.epd = load(f)
        self.positions = [pos.split(";") for pos in data]
 
    def testPerft(self):
        """Testing move generator with several positions"""
        for i in range(len(self.positions)):
            print i+1, int(self.positions[i][self.testDepth][3:])
            self.board = self.epd.loadToHistory(i, 0)[0]
            #print self.board
            self.count = 0
            self.perft(self.board, self.testDepth)
            self.assertEqual(self.count, int(self.positions[i][self.testDepth][3:]))

if __name__ == '__main__':
    unittest.main()

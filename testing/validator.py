import unittest

import __builtin__
__builtin__.__dict__['_'] = lambda s: s

from pychess.Utils.const import *
from pychess.Savers.epd import load
from pychess.Utils.validator import findMoves2, validate

MAXDEPTH = 3

class FindMovesTestCase(unittest.TestCase):
    """Move generator test using perftsuite.epd from
       http://www.albert.nu/programs/sharper/perft.htm"""
    
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
            if board[move.cord0].sign == PAWN and move.cord1.y in (0,7):
                for sign in (QUEEN, ROOK, BISHOP, KNIGHT):
                    move.promotion = sign
                    self.perft(board.move(move), depth-1)
            else:
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
            print i+1, int(self.positions[i][MAXDEPTH][3:])
            self.board = self.epd.loadToHistory(i, 0)[0]
            #print self.board
            self.count = 0
            self.perft(self.board, MAXDEPTH)
            self.assertEqual(self.count, int(self.positions[i][MAXDEPTH][3:]))

if __name__ == '__main__':
    unittest.main()

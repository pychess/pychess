import unittest

import __builtin__
__builtin__.__dict__['_'] = lambda s: s

from pychess.Utils.lmovegen import genAllMoves
from pychess.Utils.LBoard import LBoard

from pychess.Utils.bitboard import toString
from pychess.Utils.const import WHITE, PAWN, reprCord

MAXDEPTH = 3

class FindMovesTestCase(unittest.TestCase):
    """Move generator test using perftsuite.epd from
       http://www.albert.nu/programs/sharper/perft.htm"""
    
    def perft(self, board, depth):
        if depth == 0:
            self.count += 1
            return
        for move in genAllMoves(board):
            # use this only if test failes
            #print move
            #if not validate(move, board):
                #print board, move
                #return
            #print move >> 12, reprCord[(move >> 6) & 63], reprCord[move & 63]
            board.applyMove(move)
            self.perft(board, depth-1)
            board.popMove()
    
    def setUp(self):
        self.positions = []
        for line in open('gamefiles/perftsuite.epd'):
            parts = line.split(";")
            depths = [int(s[3:].rstrip()) for s in parts[1:]]
            self.positions.append( (parts[0], depths) )
    
    def testMovegen(self):
        """Testing move generator with several positions"""
        board = LBoard ()
        for i, (pos, depths) in enumerate(self.positions):
            print i, "/", len(self.positions)
            
            board.applyFen(pos)
            print toString(board.boards[WHITE][PAWN])
            hash = board.hash
            
            for depth, suposedMoveCount in enumerate(depths):
                if depth+1 > MAXDEPTH: break
                self.count = 0
                print "searching depth %d for %d moves" % (depth+1, suposedMoveCount)
                self.perft (board, depth+1)
                self.assertEqual(self.count, suposedMoveCount)
                
            self.assertEqual(board.hash, depths)
    
if __name__ == '__main__':
    unittest.main()

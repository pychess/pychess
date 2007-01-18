import unittest

import __builtin__
__builtin__.__dict__['_'] = lambda s: s

from pychess.Utils.lmovegen import genAllMoves, isCheck
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
        #print "\n".join([" "*3*depth+l for l in repr(board).split("\n")])
        for move in genAllMoves(board):
            # use this only if test failes
            #print move
            #if not validate(move, board):
                #print board, move
                #return
            board.applyMove(move)
            if isCheck(board, 1-board.color):
                board.popMove()
                continue
            #print " "*3*depth, move >> 12, reprCord[(move >> 6) & 63], reprCord[move & 63]
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
            print i+1, "/", len(self.positions)
            
            board.applyFen(pos)
            hash = board.hash
            print board
            self.assertFalse(isCheck(board, board.color))
            
            for depth, suposedMoveCount in enumerate(depths):
                if depth+1 > MAXDEPTH: break
                self.count = 0
                print "searching depth %d for %d moves" % (depth+1, suposedMoveCount)
                self.perft (board, depth+1)
                self.assertEqual(board.hash, hash)
                #print self.count
                self.assertEqual(self.count, suposedMoveCount)
            
            
            break
            
if __name__ == '__main__':
    unittest.main()

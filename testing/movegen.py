import unittest

import __builtin__
__builtin__.__dict__['_'] = lambda s: s

from pychess.Utils.lmovegen import genAllMoves, genCheckEvasions, isCheck
from pychess.Utils.LBoard import LBoard

from pychess.Utils.bitboard import toString
from pychess.Utils.Move import ltoSAN
from pychess.Utils.const import *

MAXDEPTH = 3

class FindMovesTestCase(unittest.TestCase):
    """Move generator test using perftsuite.epd from
       http://www.albert.nu/programs/sharper/perft.htm"""
    
    def perft(self, board, depth):
        if depth == 0:
            self.count += 1
            return
        
        if isCheck(board, board.color):
            nmoves = []
            for nmove in genAllMoves(board):
                board.applyMove(nmove)
                if isCheck(board, 1-board.color):
                    board.popMove()
                    continue
                nmoves.append(nmove)
                board.popMove()
            
            cmoves = [m for m in genCheckEvasions(board)]
            
            nmoves.sort()
            cmoves.sort()
            
            if nmoves == cmoves:
                for move in cmoves:
                    board.applyMove(move)
                    self.perft(board, depth-1)
                    board.popMove()
            else:
                print board
                print "nmoves"
                for move in nmoves:
                    print ltoSAN (board, move)
                print "cmoves"
                for move in cmoves:
                    print ltoSAN (board, move)
                self.assertEqual(nmoves, cmoves)
        else:
            for move in genAllMoves(board):
                board.applyMove(move)
                if isCheck(board, 1-board.color):
                    board.popMove()
                    continue
                #if depth == 5:
                #board.popMove()
                #print "   "*(2-depth)+ltoSAN (board, move)
                #board.applyMove(move)
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
            print pos
            print board
            
            for depth, suposedMoveCount in enumerate(depths):
                if depth+1 > MAXDEPTH: break
                self.count = 0
                print "searching depth %d for %d moves" % (depth+1, suposedMoveCount)
                #print board
                self.perft (board, depth+1)
                self.assertEqual(board.hash, hash)
                self.assertEqual(self.count, suposedMoveCount)
            print
            
if __name__ == '__main__':
    unittest.main()

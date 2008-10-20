import unittest

import __builtin__
__builtin__.__dict__['_'] = lambda s: s

import random
import operator

from pychess.Utils.lutils.bitboard import *

class BitboardTestCase(unittest.TestCase):
    
    def setUp (self):
        self.positionSets = []
        # Random positions. Ten of each length. Will also include range(64) and
        # range(0)
        for i in xrange(10):
            for length in xrange(64):
                if length:
                    positions = random.sample(xrange(64), length)
                    board = reduce(operator.or_, (1<<(63-i) for i in positions))
                    self.positionSets.append( (positions, createBoard(board)) )
                else:
                    self.positionSets.append( ([], createBoard(0)) )
    
    def test1(self):
        """Testing setbit and clearbit"""
        
        for positions,board in self.positionSets:
            b = createBoard(0)
            for pos in positions:
                b = setBit(b, pos)
            self.assertEqual(b, board)
            
            for pos in positions:
                b = clearBit(b, pos)
            self.assertEqual(b, createBoard(0))
    
    def test2(self):
        """Testing firstbit and lastbit"""
        
        for positions,board in self.positionSets:
            if positions:
                positions.sort()
                self.assertEqual(positions[0], firstBit(board))
                self.assertEqual(positions[-1], lastBit(board))

    def test3(self):
        """Testing bitlength"""
        
        for positions,board in self.positionSets:
            self.assertEqual(len(positions), bitLength(board))
    
    def test4(self):
        """Testing iterbits"""
        
        for positions,board in self.positionSets:
            positions.sort()
            itered = list(iterBits(board))
            itered.sort()
            self.assertEqual(positions, itered)

if __name__ == '__main__':
    unittest.main()

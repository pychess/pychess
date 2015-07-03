import unittest

import random
import operator
from functools import reduce

from pychess.Utils.lutils.bitboard import *

class BitboardTestCase(unittest.TestCase):
    
    def setUp (self):
        self.positionSets = []
        # Random positions. Ten of each length. Will also include range(64) and
        # range(0)
        for i in range(10):
            for length in range(64):
                if length:
                    positions = random.sample(range(64), length)
                    board = reduce(operator.or_, (1<<(63-i) for i in positions))
                    self.positionSets.append( (positions, board) )
                else:
                    self.positionSets.append( ([], 0) )
    
    def test1(self):
        """Testing setbit and clearbit"""
        
        for positions,board in self.positionSets:
            b = 0
            for pos in positions:
                b = setBit(b, pos)
            self.assertEqual(b, board)
            
            for pos in positions:
                b = clearBit(b, pos)
            self.assertEqual(b, 0)
    
    def test2(self):
        """Testing firstbit and lastbit"""
        
        for positions,board in self.positionSets:
            if positions:
                positions.sort()
                self.assertEqual(positions[0], firstBit(board))
                self.assertEqual(positions[-1], lastBit(board))

    def test3(self):
        """Testing iterbits"""
        
        for positions,board in self.positionSets:
            positions.sort()
            itered = sorted(iterBits(board))
            self.assertEqual(positions, itered)

if __name__ == '__main__':
    unittest.main()

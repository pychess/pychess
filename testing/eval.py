import unittest

import __builtin__
__builtin__.__dict__['_'] = lambda s: s

from pychess.Utils.const import *
from pychess.Utils.lutils.leval import evaluateComplete
from pychess.Utils.lutils.leval import LBoard


class EvalTestCase(unittest.TestCase):
    
    def setUp (self):
        self.board = LBoard()
    
    def testStartboardScore_1(self):
        """Testing eval symmetry with startboard (WHITE)"""
        score = evaluateComplete(self.board, color=WHITE, balanced=True)
        self.assertEqual(score, 0)
    
    def testStartboardScore_2(self):
        """Testing eval symmetry with startboard (BLACK)"""
        score = evaluateComplete(self.board, color=BLACK, balanced=True)
        self.assertEqual(score, 0)

if __name__ == '__main__':
    unittest.main()

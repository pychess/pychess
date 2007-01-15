import unittest

from pychess.Utils.const import *
from pychess.Utils.History import startBoard
from pychess.Utils.eval import evaluateComplete


class EvalTestCase(unittest.TestCase):
    
    def setUp(self):
        self.board = startBoard()
        
    def testStartboardScore_1(self):
        """Testing eval symmetry with startboard (WHITE)"""
        score = evaluateComplete(self.board, color=WHITE)
        self.assertEqual(score, 0)

    def testStartboardScore_2(self):
        """Testing eval symmetry with startboard (BLACK)"""
        score = evaluateComplete(self.board, color=BLACK)
        self.assertEqual(score, 0)

if __name__ == '__main__':
    unittest.main()

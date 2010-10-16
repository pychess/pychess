import unittest

from pychess.Utils.const import *
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.leval import evaluateComplete
from pychess.Utils.lutils import leval 


class EvalTestCase(unittest.TestCase):
    
    def setUp (self):
        self.board = LBoard(NORMALCHESS)
        self.board.applyFen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1")
    
    def test1(self):
        """Testing eval symmetry with startboard (WHITE)"""
        score = evaluateComplete(self.board, color=WHITE, balanced=True)
        self.assertEqual(score, 0)
    
    def test2(self):
        """Testing eval symmetry with startboard (BLACK)"""
        score = evaluateComplete(self.board, color=BLACK, balanced=True)
        self.assertEqual(score, 0)
    
    def test3(self):
        """Testing eval symmetry between colors with balanced=False"""
        scorew = evaluateComplete(self.board, color=WHITE)
        scoreb = evaluateComplete(self.board, color=BLACK)
        self.assertEqual(scorew, scoreb)
    
    def test4(self):
        """Testing symetry of each function"""
        funcs = (f for f in dir(leval) if f.startswith("eval"))
        funcs = (getattr(leval,f) for f in funcs)
        funcs = (f for f in funcs if callable(f) and f != leval.evalMaterial)
        
        sw, phasew = leval.evalMaterial (self.board, WHITE)
        sb, phaseb = leval.evalMaterial (self.board, BLACK)
        self.assertEqual(phasew, phaseb)
        
        for func in funcs:
            sw = func(self.board, WHITE, phasew)
            sb = func(self.board, BLACK, phaseb)
            print func, sw, sb
            self.assertEqual(sw, sb)
    
if __name__ == '__main__':
    unittest.main()

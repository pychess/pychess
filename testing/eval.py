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
        score = evaluateComplete(self.board, color=WHITE)
        self.assertEqual(score, 0)
    
    def test2(self):
        """Testing eval symmetry with startboard (BLACK)"""
        score = evaluateComplete(self.board, color=BLACK)
        self.assertEqual(score, 0)
    
    def test3(self):
        """Testing eval symmetry of each function"""
        funcs = (f for f in dir(leval) if f.startswith("eval"))
        funcs = (getattr(leval,f) for f in funcs)
        funcs = (f for f in funcs if callable(f) \
                                    and f != leval.evaluateComplete\
                                    and f != leval.evalMaterial\
                                    and f != leval.evalPawnStructure\
                                    and f != leval.evalTrappedBishops)
        
        sw, phasew = leval.evalMaterial (self.board, WHITE)
        sb, phaseb = leval.evalMaterial (self.board, BLACK)

        self.assertEqual(phasew, phaseb)
        
        pawnScore, passed, weaked = leval.cacheablePawnInfo (self.board, phasew)
        sw = leval.evalPawnStructure (self.board, WHITE, phasew, passed, weaked)

        pawnScore, passed, weaked = leval.cacheablePawnInfo (self.board, phaseb)
        sb = leval.evalPawnStructure (self.board, BLACK, phaseb, passed, weaked)

        self.assertEqual(sw, sb)

        sw = leval.evalTrappedBishops (self.board, WHITE)
        sb = leval.evalTrappedBishops (self.board, BLACK)

        self.assertEqual(sw, sb)

        for func in funcs:
            sw = func(self.board, WHITE, phasew)
            sb = func(self.board, BLACK, phaseb)
            #print func, sw, sb
            self.assertEqual(sw, sb)
    
if __name__ == '__main__':
    unittest.main()

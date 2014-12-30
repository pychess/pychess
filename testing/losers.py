# -*- coding: UTF-8 -*-

from __future__ import print_function

import sys
import unittest

from pychess.Utils.const import LOSERSCHESS
from pychess.Utils.logic import validate
from pychess.Utils.Move import Move, parseSAN
from pychess.Variants.losers import LosersBoard

# ♚ . . ♔ . . . . 
# ♙ . . . . . . . 
# . . . . . . . . 
# . . . . . . . . 
# . . . . . . . . 
# . . . . . . . . 
# . . . . . . . . 
FEN0 = "k2K4/P7/8/8/8/8/8/8 b - - 0 1"

# ♚ . . ♔ . . . . 
# ♙ . . . . . . . 
# . ♙ . . . . . . 
# . . . . . . . . 
# . . . . . . . . 
# . . . . . . . . 
# . . . . . . . . 
FEN1 = "k2K4/P7/1P6/8/8/8/8/8 b - - 0 1"

# ♚ . . ♔ . . . . 
# ♜ ♙ . . . . . . 
# . . ♙ . . . . . 
# . . . . . . . . 
# . . . . . . . . 
# . . . . . . . . 
# . . . . . . . . 
FEN2 = "k2K4/rP6/2P5/8/8/8/8/8 b - - 0 1"

class LosersTestCase(unittest.TestCase):
    
    def test_validate(self):
        """Testing validate move in Losers variant"""

        board = LosersBoard(setup=FEN0)
        print(board)
        self.assertTrue(validate(board, parseSAN(board, 'Kxa7')))
        self.assertTrue(not validate(board, parseSAN(board, 'Kb8')))
        self.assertTrue(not validate(board, parseSAN(board, 'Kb7')))
        
        board = LosersBoard(setup=FEN1)
        print(board)
        self.assertTrue(not validate(board, parseSAN(board, 'Kxa7')))
        self.assertTrue(not validate(board, parseSAN(board, 'Kb8')))
        self.assertTrue(validate(board, parseSAN(board, 'Kb7')))

        board = LosersBoard(setup=FEN2)
        print(board)
        self.assertTrue(not validate(board, parseSAN(board, 'Kxb7')))
        self.assertTrue(not validate(board, parseSAN(board, 'Kb8')))
        self.assertTrue(validate(board, parseSAN(board, 'Rxb7')))

if __name__ == '__main__':
    unittest.main()

# -*- coding: UTF-8 -*-

from __future__ import print_function

import sys
import unittest

from pychess.Utils.const import SITTUYINCHESS
from pychess.Utils.logic import validate
from pychess.Utils.Move import Move, parseSAN
from pychess.Variants.asean import SittuyinBoard

# . . . ♜ . ♜ . . 
# . . . . ♝ ♛ . . 
# ♚ ♞ . ♝ . . . ♟ 
# . . . . ♟ . ♟ ♙ 
# . . . . ♙ ♟ ♙ . 
# ♙ . ♖ ♗ ♘ . . . 
# . ♟ . ♕ ♔ ♗ . . 
# . . ♖ . . . . . 
FEN0 = "3r1r2/4sf2/kn1s3p/4p1pP/4PpP1/P1RSN3/1p1FKS2/2R5 b - - 1 21"

# . . . ♜ . ♜ . . 
# . . . . ♝ . . . 
# ♚ ♞ . ♝ . . . ♟ 
# . . . . ♟ . ♟ ♙ 
# . . . . ♙ ♟ ♙ . 
# ♙ . ♖ ♗ ♘ . . . 
# . ♟ . ♕ ♔ ♗ . . 
# . . ♖ . . . . . 
FEN1 = "3r1r2/4s3/kn1s3p/4p1pP/4PpP1/P1RSN3/1p1FKS2/2R5 b - - 1 21"


class SittuyinTestCase(unittest.TestCase):
    
    def test_validate(self):
        """Testing validate move in Sittuyin variant"""

        board = SittuyinBoard(setup=FEN0)
        print(board)
        # no promotion if we have Met (queen)
        self.assertTrue(validate(board, parseSAN(board, 'f4f3')))
        self.assertTrue(validate(board, parseSAN(board, 'b2b1')))
        self.assertTrue(validate(board, parseSAN(board, 'bxc1')))
        self.assertTrue(not validate(board, parseSAN(board, 'f4f3f')))
        self.assertTrue(not validate(board, parseSAN(board, 'b2b2f')))
        self.assertTrue(not validate(board, parseSAN(board, 'b2b1f')))
        self.assertTrue(not validate(board, parseSAN(board, 'bxc1f')))
        
        board = SittuyinBoard(setup=FEN1)
        print(board)
        # but (optional) promotion if we don't have Met (queen)
        self.assertTrue(validate(board, parseSAN(board, 'f4f3f')))
        self.assertTrue(validate(board, parseSAN(board, 'b2b2f')))
        self.assertTrue(validate(board, parseSAN(board, 'b2b1')))
        self.assertTrue(validate(board, parseSAN(board, 'bxc1')))
        self.assertTrue(validate(board, parseSAN(board, 'f4f3')))
        self.assertTrue(not validate(board, parseSAN(board, 'b2b2')))
        self.assertTrue(not validate(board, parseSAN(board, 'b2b1f')))
        self.assertTrue(not validate(board, parseSAN(board, 'bxc1f')))

if __name__ == '__main__':
    unittest.main()

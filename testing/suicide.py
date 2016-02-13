# -*- coding: UTF-8 -*-

from __future__ import print_function

import unittest

from pychess.Utils.logic import validate
from pychess.Utils.Move import parseSAN
from pychess.Variants.suicide import SuicideBoard

# ♚ . . ♔ . . . .
# ♙ . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
FEN0 = "k2K4/P7/8/8/8/8/8/8 b - - 0 1"

# ♚ ♔ . . . . . .
# ♙ . . . . . . .
# . ♙ . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
FEN1 = "kK6/P7/1P6/8/8/8/8/8 b - - 0 1"

# ♚ . . ♔ . . . .
# . ♙ . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
FEN2 = "k2K4/1P6/8/8/8/8/8/8 b - - 0 1"

# ♔ . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . ♚ . . . . .
# . . . . . ♟ . .
# . . . . ♚ . . .
FEN3 = "K7/8/8/8/8/2k5/5p2/4k3 b - - 0 1"


class SuicideTestCase(unittest.TestCase):
    def test_validate(self):
        """Testing validate move in Suicide variant"""

        # board = SuicideBoard(setup=FEN0)
        # print board
        # self.assertTrue(validate(board, parseSAN(board, 'Kxa7')))
        # self.assertTrue(not validate(board, parseSAN(board, 'Kb8')))
        # self.assertTrue(not validate(board, parseSAN(board, 'Kb7')))

        # board = SuicideBoard(setup=FEN1)
        # print board
        # self.assertTrue(validate(board, parseSAN(board, 'Kxa7')))
        # self.assertTrue(validate(board, parseSAN(board, 'Kxb8')))
        # self.assertTrue(not validate(board, parseSAN(board, 'Kb7')))

        # board = SuicideBoard(setup=FEN2)
        # print board
        # self.assertTrue(not validate(board, parseSAN(board, 'Ka7')))
        # self.assertTrue(not validate(board, parseSAN(board, 'Kb8')))
        # self.assertTrue(validate(board, parseSAN(board, 'Kxb7')))

        board = SuicideBoard(setup=FEN3)
        print(board)
        self.assertTrue(validate(board, parseSAN(board, 'Ked2')))


if __name__ == '__main__':
    unittest.main()

# -*- coding: UTF-8 -*-


import unittest

from pychess.Utils.logic import validate
from pychess.Utils.Move import parseSAN
from pychess.Variants.placement import PlacementBoard

# . . . . . . . .
# ♟ ♟ ♟ ♟ ♟ ♟ ♟ ♟
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# ♙ ♙ ♙ ♙ ♙ ♙ ♙ ♙
# . . . . . . . .
#
# [♞♞♝♝♜♜♛♚]
# [♘♘♗♗♖♖♕♔]
FEN0 = "8/pppppppp/8/8/8/8/PPPPPPPP/8/nnbbrrqkNNBBRRQK w - - 0 1"

# . . . . . . . .
# ♟ ♟ ♟ ♟ ♟ ♟ ♟ ♟
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# ♙ ♙ ♙ ♙ ♙ ♙ ♙ ♙
# . . . . ♔ . . .
#
# [♞♞♝♝♜♜♛♚]
# [♘♘♗♗♖♖♕]
FEN1 = "8/pppppppp/8/8/8/8/PPPPPPPP/4K3/nnbbrrqkNNBBRRQ b - - 1 1"

# . . . ♛ ♚ ♜ . ♜
# ♟ ♟ ♟ ♟ ♟ ♟ ♟ ♟
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# ♙ ♙ ♙ ♙ ♙ ♙ ♙ ♙
# . . . ♕ ♔ ♖ . ♖
#
# [♞♞♝♝]
# [♘♘♗♗]
FEN2 = "3qkr1r/pppppppp/8/8/8/8/PPPPPPPP/3QKR1R/nnbbNNBB w - - 8 5"

# ♝ . . ♛ ♚ ♜ . ♜
# ♟ ♟ ♟ ♟ ♟ ♟ ♟ ♟
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# ♙ ♙ ♙ ♙ ♙ ♙ ♙ ♙
# ♗ . . ♕ ♔ ♖ . ♖
#
# [♞♞♝]
# [♘♘♗]
FEN3 = "b2qkr1r/pppppppp/8/8/8/8/PPPPPPPP/B2QKR1R/nnbNNB w - - 10 6"


class PlacementTestCase(unittest.TestCase):
    def test_validate(self):
        """Testing validate move in Placement variant"""

        board = PlacementBoard(setup=FEN0)
        print(board)
        # only drop moves to base line allowed
        self.assertTrue(validate(board, parseSAN(board, 'K@a1')))
        self.assertTrue(validate(board, parseSAN(board, 'K@b1')))
        self.assertTrue(validate(board, parseSAN(board, 'K@h1')))
        self.assertTrue(not validate(board, parseSAN(board, 'K@a2')))
        self.assertTrue(not validate(board, parseSAN(board, 'K@a3')))
        self.assertTrue(not validate(board, parseSAN(board, 'K@a8')))
        self.assertTrue(not validate(board, parseSAN(board, 'b4')))

        board = PlacementBoard(setup=FEN1)
        print(board)
        # only drop moves to base line allowed
        self.assertTrue(validate(board, parseSAN(board, 'K@a8')))
        self.assertTrue(validate(board, parseSAN(board, 'K@b8')))
        self.assertTrue(validate(board, parseSAN(board, 'K@h8')))
        self.assertTrue(not validate(board, parseSAN(board, 'K@a7')))
        self.assertTrue(not validate(board, parseSAN(board, 'K@a6')))
        self.assertTrue(not validate(board, parseSAN(board, 'K@a1')))
        self.assertTrue(not validate(board, parseSAN(board, 'b5')))

        board = PlacementBoard(setup=FEN2)
        print(board)
        # bishops have to be placed on opposite colored fields
        self.assertTrue(validate(board, parseSAN(board, 'B@a1')))
        self.assertTrue(validate(board, parseSAN(board, 'B@b1')))
        self.assertTrue(validate(board, parseSAN(board, 'B@c1')))
        self.assertTrue(validate(board, parseSAN(board, 'B@g1')))
        self.assertTrue(validate(board, parseSAN(board, 'N@a1')))
        self.assertTrue(validate(board, parseSAN(board, 'N@c1')))
        self.assertTrue(validate(board, parseSAN(board, 'N@g1')))
        self.assertTrue(not validate(board, parseSAN(board, 'N@b1')))

        board = PlacementBoard(setup=FEN3)
        print(board)
        # bishops have to be placed on opposite colored fields
        self.assertTrue(validate(board, parseSAN(board, 'B@b1')))
        self.assertTrue(validate(board, parseSAN(board, 'N@c1')))
        self.assertTrue(validate(board, parseSAN(board, 'N@g1')))
        self.assertTrue(not validate(board, parseSAN(board, 'B@c1')))
        self.assertTrue(not validate(board, parseSAN(board, 'B@g1')))
        self.assertTrue(not validate(board, parseSAN(board, 'N@b1')))


if __name__ == '__main__':
    unittest.main()

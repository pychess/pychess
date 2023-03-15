import unittest

from pychess.Utils.const import LIGHTBRIGADECHESS
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import toAN
from pychess.Utils.lutils.lmovegen import genAllMoves


def placement(fen):
    return fen.split()[0]


class SchessTestCase(unittest.TestCase):
    def test_white_promotion(self):
        FEN = "k7/7P/8/8/8/8/8/7K w - - 0 1"
        board = LBoard(LIGHTBRIGADECHESS)
        board.applyFen(FEN)
        print("--------")
        print(board)

        moves = set()
        for move in genAllMoves(board):
            moves.add(toAN(board, move))

        self.assertIn("h7h8=Q", moves)
        self.assertNotIn("h7h8", moves)
        self.assertNotIn("h7h8=R", moves)
        self.assertNotIn("h7h8=B", moves)
        self.assertNotIn("h7h8=N", moves)
        self.assertNotIn("h7h8=K", moves)

    def test_black_promotion(self):
        FEN = "k7/8/8/8/8/8/p7/7K b - - 0 1"
        board = LBoard(LIGHTBRIGADECHESS)
        board.applyFen(FEN)
        print("--------")
        print(board)

        moves = set()
        for move in genAllMoves(board):
            moves.add(toAN(board, move))

        self.assertIn("a2a1=N", moves)
        self.assertNotIn("a2a1", moves)
        self.assertNotIn("a2a1=R", moves)
        self.assertNotIn("a2a1=B", moves)
        self.assertNotIn("a2a1=Q", moves)
        self.assertNotIn("a2a1=K", moves)


if __name__ == '__main__':
    unittest.main()

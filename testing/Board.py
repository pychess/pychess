import unittest

from pychess.Utils.const import BLACK, KING, ROOK, D2, D4, G8, F6, C2, C4, G7, G6, G2, G3, F8, F1, E8, H8
from pychess.Utils.Cord import Cord
from pychess.Utils.Board import Board
from pychess.Utils.Move import Move
from pychess.Utils.Piece import Piece


class BoardTestCase(unittest.TestCase):
    def test1(self):
        """ Testing Board.move() on frc castling in non frc game """
        board = Board(setup=True)

        moves = ((D2, D4), (G8, F6), (C2, C4), (G7, G6), (G2, G3), (F8, G7), (F1, G2), (E8, H8))

        for cord0, cord1 in moves:
            print(cord0, cord1)
            board = board.move(Move(Cord(cord0), Cord(cord1), board))
            board.printPieces()

        self.assertIsNone(board[Cord(E8)])
        self.assertIsNone(board[Cord(H8)])

        self.assertEqual(board[Cord(G8)].piece, Piece(BLACK, KING).piece)
        self.assertEqual(board[Cord(F8)].piece, Piece(BLACK, ROOK).piece)


if __name__ == '__main__':
    unittest.main()

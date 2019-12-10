import unittest

from pychess.Utils.const import WHITE, BLACK, E4, E5, CORD_CONST
from pychess.Utils.Cord import Cord
from pychess.Utils.Board import Board
from pychess.Utils.Move import Move
from pychess.Utils.DecisionSupportAlgorithm import DecisionSupportAlgorithm


class BoardTestCase(unittest.TestCase):
    def test(self):
        """ Testing what recognize the algorithm """
        board = Board(setup=True)
        dsa = DecisionSupportAlgorithm()
        dsa.set_foe_as_bot()

        moves = ((CORD_CONST["e2"], CORD_CONST["e4"]), (CORD_CONST["d7"], CORD_CONST["d5"]))

        for cord0, cord1 in moves:
            board = board.move(Move(Cord(cord0), Cord(cord1), board))
            board.printPieces()

        # Not protected
        self.assertEqual(dsa.attacked_and_not_protected(board, WHITE), [Cord("e4")])

        # protected by Queen
        self.assertEqual(dsa.attacked_and_not_protected(board, BLACK), [])

        board = board.move(Move(Cord(E4), Cord(E5), board))

        self.assertEqual(dsa.attacked_and_not_protected(board, WHITE), [])


if __name__ == '__main__':
    unittest.main()

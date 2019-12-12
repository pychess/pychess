import unittest

from pychess.Utils.const import WHITE, BLACK, E4, E5, CORD_CONST
from pychess.Utils.Cord import Cord
from pychess.Utils.Board import Board
from pychess.Utils.Move import Move
from pychess.Utils.DecisionSupportAlgorithm import DecisionSupportAlgorithm


class BoardTestCase(unittest.TestCase):
    def testNotProtected(self):
        board = Board(setup=True)
        dsa = DecisionSupportAlgorithm()
        dsa.set_foe_as_bot()
        dsa.enableDisableAlgo(True)

        # at the start of the game, only the two towers are not protected by other pieces
        self.assertEqual(
            set([Cord("a1", color="Y"), Cord("h1", color="Y")]),
            set(dsa._DecisionSupportAlgorithm__not_protected(board, WHITE))
        )

        board = board.move(Move(Cord(CORD_CONST["e2"]), Cord(CORD_CONST["e4"]), board))

        # the pawn moved to e4 is now not protected
        self.assertEqual(
            set([Cord("a1", color="Y"), Cord("h1", color="Y"), Cord("e4", color="Y")]),
            set(dsa._DecisionSupportAlgorithm__not_protected(board, WHITE))
        )

        board = board.move(Move(Cord(CORD_CONST["d7"]), Cord(CORD_CONST["d5"]), board))

        # the black pawn attack the white pawn, it is not notProtected that will detect this case,
        # only the two towers are not protected
        self.assertEqual(
            set([Cord("a1", color="Y"), Cord("h1", color="Y")]),
            set(dsa._DecisionSupportAlgorithm__not_protected(board, WHITE))
        )

    def testAttackedAndNotProtected(self):
        """ Testing what recognize the algorithm """
        board = Board(setup=True)
        dsa = DecisionSupportAlgorithm()
        dsa.set_foe_as_bot()
        dsa.enableDisableAlgo(True)

        moves = ((CORD_CONST["e2"], CORD_CONST["e4"]), (CORD_CONST["d7"], CORD_CONST["d5"]))

        for cord0, cord1 in moves:
            board = board.move(Move(Cord(cord0), Cord(cord1), board))
            board.printPieces()

        # Not protected
        self.assertEqual([Cord("e4", color="R")], dsa._DecisionSupportAlgorithm__attacked_and_not_protected(board, WHITE))

        # protected by Queen
        self.assertEqual([], dsa._DecisionSupportAlgorithm__attacked_and_not_protected(board, BLACK))

        board = board.move(Move(Cord(E4), Cord(E5), board))

        self.assertEqual([], dsa._DecisionSupportAlgorithm__attacked_and_not_protected(board, WHITE))


    def testAll(self):
        board = Board(setup=True)
        dsa = DecisionSupportAlgorithm()
        dsa.set_foe_as_bot()
        dsa.enableDisableAlgo(True)

        moves = ((CORD_CONST["e2"], CORD_CONST["e4"]), (CORD_CONST["d7"], CORD_CONST["d5"]))

        for cord0, cord1 in moves:
            board = board.move(Move(Cord(cord0), Cord(cord1), board))
            board.printPieces()

        # Not protected
        self.assertEqual(
            set([Cord("a1", color="Y"), Cord("h1", color="Y"), Cord("e4", color="R")]),
            set(dsa.calculate_coordinate_in_danger(board, WHITE))
        )

        # protected by Queen, so no danger
        self.assertEqual(
            set([Cord("a8", color="Y"), Cord("h8", color="Y")]),
            set(dsa.calculate_coordinate_in_danger(board, BLACK))
        )

        # pawn go forward, no danger
        board = board.move(Move(Cord(E4), Cord(E5), board))
        self.assertEqual(
            set([Cord("a1", color="Y"), Cord("h1", color="Y"), Cord("e5", color="Y")]),
            set(dsa.calculate_coordinate_in_danger(board, WHITE))
        )

if __name__ == '__main__':
    unittest.main()

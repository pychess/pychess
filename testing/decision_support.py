import unittest

from pychess.Utils.const import WHITE, BLACK, E4, E5, cordDic
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
        coordinate_not_protected = dsa._DecisionSupportAlgorithm__apply_algorithm(
            board, WHITE,
            dsa._DecisionSupportAlgorithm__not_protected
        )

        self.assertEqual(
            {Cord("a1", color="Y"), Cord("h1", color="Y")},
            set(coordinate_not_protected)
        )

        board = board.move(Move(Cord(cordDic["e2"]), Cord(cordDic["e4"]), board))

        coordinate_not_protected = dsa._DecisionSupportAlgorithm__apply_algorithm(
            board, WHITE,
            dsa._DecisionSupportAlgorithm__not_protected
        )

        # the pawn moved to e4 is now not protected
        self.assertEqual(
            {Cord("a1", color="Y"), Cord("h1", color="Y"), Cord("e4", color="Y")},
            set(coordinate_not_protected)
        )

        board = board.move(Move(Cord(cordDic["d7"]), Cord(cordDic["d5"]), board))

        # the black pawn attack the white pawn, it is not notProtected that will detect this case,
        # only the two towers are not protected

        coordinate_not_protected = dsa._DecisionSupportAlgorithm__apply_algorithm(
            board, WHITE,
            dsa._DecisionSupportAlgorithm__not_protected
        )

        self.assertEqual(
            {Cord("a1", color="Y"), Cord("h1", color="Y")},
            set(coordinate_not_protected)
        )

    def testAttackedAndNotProtected(self):
        """ Testing what recognize the algorithm """
        board = Board(setup=True)
        dsa = DecisionSupportAlgorithm()
        dsa.set_foe_as_bot()
        dsa.enableDisableAlgo(True)

        moves = ((cordDic["e2"], cordDic["e4"]), (cordDic["d7"], cordDic["d5"]))

        for cord0, cord1 in moves:
            board = board.move(Move(Cord(cord0), Cord(cord1), board))

        coordinate_attacked = dsa._DecisionSupportAlgorithm__apply_algorithm(
            board, WHITE,
            dsa._DecisionSupportAlgorithm__attacked_and_not_protected
        )

        # Not protected
        self.assertEqual([Cord("e4", color="R")], coordinate_attacked)

        coordinate_attacked = dsa._DecisionSupportAlgorithm__apply_algorithm(
            board, BLACK,
            dsa._DecisionSupportAlgorithm__attacked_and_not_protected
        )

        # protected by Queen
        self.assertEqual([], coordinate_attacked)

        board = board.move(Move(Cord(E4), Cord(E5), board))

        coordinate_attacked = dsa._DecisionSupportAlgorithm__apply_algorithm(
            board, WHITE,
            dsa._DecisionSupportAlgorithm__attacked_and_not_protected
        )

        self.assertEqual([], coordinate_attacked)

    def testAll(self):
        board = Board(setup=True)
        dsa = DecisionSupportAlgorithm()
        dsa.set_foe_as_bot()
        dsa.enableDisableAlgo(True)

        moves = ((cordDic["e2"], cordDic["e4"]), (cordDic["d7"], cordDic["d5"]))

        for cord0, cord1 in moves:
            board = board.move(Move(Cord(cord0), Cord(cord1), board))
        board.printPieces()

        # Not protected
        self.assertEqual(
            {Cord("a1", color="Y"), Cord("h1", color="Y"), Cord("e4", color="R")},
            set(dsa.calculate_coordinate_in_danger(board, WHITE))
        )

        # protected by Queen, so no danger
        self.assertEqual(
            {Cord("a8", color="Y"), Cord("h8", color="Y")},
            set(dsa.calculate_coordinate_in_danger(board, BLACK))
        )

        # pawn go forward, no danger
        board = board.move(Move(Cord(E4), Cord(E5), board))
        self.assertEqual(
            {Cord("a1", color="Y"), Cord("h1", color="Y"), Cord("e5", color="Y")},
            set(dsa.calculate_coordinate_in_danger(board, WHITE))
        )

        # Should not recognize king
        board_king = Board(setup=True)
        dsa_king = DecisionSupportAlgorithm()
        dsa_king.set_foe_as_bot()
        dsa_king.enableDisableAlgo(True)

        moves = ((cordDic["e2"], cordDic["e4"]), (cordDic["f7"], cordDic["f5"]), (cordDic["d1"], cordDic["h5"]))

        for cord0, cord1 in moves:
            board_king = board_king.move(Move(Cord(cord0), Cord(cord1), board_king))
            # board_king.printPieces()

        self.assertEqual(
            {Cord("a8", color="Y"), Cord("h8", color="Y"), Cord("f5", color="Y")},
            set(dsa.calculate_coordinate_in_danger(board_king, BLACK))
        )


if __name__ == '__main__':
    unittest.main()

import unittest

from pychess.Utils.Board import Board
from pychess.Utils.GameModel import GameModel
from pychess.Utils.Move import listToMoves


class GameModelVariationTests(unittest.TestCase):
    def test_insert_engine_pv_from_initial_fen(self):
        model = GameModel()
        board = Board("7k/8/8/8/8/8/8/K6R w - - 0 23")
        model.boards = [board]
        model.variations = [model.boards]

        self.assertIsNone(model.add_variation(board, []))
        self.assertIsNone(board.board.next)

        moves = listToMoves(board, ["Kb1", "Kg8", "Kc2"], validate=True)
        variation = model.add_variation(board, moves)

        self.assertIsNotNone(variation)
        self.assertEqual(len(model.variations), 2)
        self.assertIs(variation[0], board)
        self.assertEqual(
            variation[-1].asFen(),
            "6k1/8/8/8/8/8/2K5/7R b - - 3 24",
        )

        parent = board.board.next
        self.assertIsNotNone(parent)
        self.assertFalse(parent.fen_was_applied)
        self.assertIs(parent.prev, board.board)
        self.assertEqual(len(parent.children), 1)
        self.assertEqual(len(parent.children[0]), len(moves) + 1)

        other_moves = listToMoves(board, ["Ka2", "Kg8", "Kb3"], validate=True)
        other_variation = model.add_variation(board, other_moves)
        self.assertIs(board.board.next, parent)
        self.assertEqual(len(parent.children), 2)

        model.remove_variation(variation[1].board, parent)
        self.assertIs(board.board.next, parent)
        self.assertEqual(len(parent.children), 1)
        self.assertEqual(len(model.variations), 2)

        model.remove_variation(other_variation[1].board, parent)
        self.assertIsNone(board.board.next)
        self.assertEqual(model.variations, [model.boards])


if __name__ == "__main__":
    unittest.main()

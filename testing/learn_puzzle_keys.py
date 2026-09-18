import unittest
from unittest.mock import patch

from pychess.Utils.const import PUZZLE
from pychess.perspectives.learn import PuzzlesPanel


class StubMove:
    def __init__(self, uci):
        self.uci = uci

    def as_uci(self):
        return self.uci


class AuthoredPgnKeyTest(unittest.TestCase):
    def test_mate_in_three_uses_pgn_key(self):
        with patch.object(PuzzlesPanel, "start_puzzle_game") as start_puzzle_game:
            PuzzlesPanel.start_puzzle_from("mate_in_3.pgn", 0)

        gamemodel = start_puzzle_game.call_args.args[0]
        self.assertEqual(gamemodel.authored_pgn_key, "c4b5")

        gamemodel.set_learn_data(PUZZLE, "mate_in_3.pgn")
        self.assertEqual(gamemodel.hints[gamemodel.lowply], [("c4b5", 10000)])

        gamemodel.moves[:] = [StubMove("c4b5")]
        self.assertTrue(gamemodel._check_authored_pgn_key_move())

        gamemodel.moves[:] = [StubMove("c4d3")]
        self.assertFalse(gamemodel._check_authored_pgn_key_move())

        gamemodel.moves[:] = [StubMove("c4b5"), StubMove("c7c6"), StubMove("b5e2")]
        self.assertIsNone(gamemodel._check_authored_pgn_key_move())


if __name__ == "__main__":
    unittest.main(verbosity=2)

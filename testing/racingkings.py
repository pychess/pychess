import unittest

from pychess.Utils.const import (
    BLACKWON,
    DRAW,
    DRAW_KINGSINEIGHTROW,
    RUNNING,
    UNKNOWN_REASON,
    WHITEWON,
    WON_KINGINEIGHTROW,
)
from pychess.Utils.logic import validate, getStatus
from pychess.Utils.Move import parseSAN
from pychess.Variants.racingkings import RacingKingsBoard

# . . ♜ . . . ♖ .
# . . ♚ . . . . ♔
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
FEN = "2r3R1/2k4K/8/8/8/8/8/8 w - - 0 1"


class RacingKingsTestCase(unittest.TestCase):
    def test1(self):
        """Testing both king goes to 8.row draw in racingkings variant"""

        board = RacingKingsBoard(setup=FEN)
        board = board.move(parseSAN(board, "Kh8"))
        print(board)
        # White king reached 8th row, but this is not a win
        # because black can reach 8th row also with hes next move
        self.assertEqual(getStatus(board), (RUNNING, UNKNOWN_REASON))

        self.assertTrue(validate(board, parseSAN(board, "Kb8")))
        self.assertTrue(not validate(board, parseSAN(board, "Kd8")))

        board = board.move(parseSAN(board, "Kb8"))
        print(board)
        self.assertEqual(getStatus(board), (DRAW, DRAW_KINGSINEIGHTROW))

    def test_win_after_opponent_fails_to_draw_white(self):
        """Issue #1889: once White's king is on the back rank and Black cannot
        (or chooses not to) also reach it, the game must be over with White
        winning -- even when it is White's turn again. Previously this stayed
        RUNNING and the board kept accepting moves."""
        # White king on the back rank, Black king off it, White to move.
        board = RacingKingsBoard(setup="7K/k7/8/8/8/8/8/8 w - - 0 1")
        self.assertEqual(getStatus(board), (WHITEWON, WON_KINGINEIGHTROW))

    def test_win_after_opponent_fails_to_draw_black(self):
        """Symmetric case: Black's king on the back rank, White off it, Black
        to move -> Black wins."""
        board = RacingKingsBoard(setup="k7/7K/8/8/8/8/8/8 b - - 0 1")
        self.assertEqual(getStatus(board), (BLACKWON, WON_KINGINEIGHTROW))

    def test_both_kings_on_back_rank_is_draw(self):
        """Regression guard: both kings on the back rank is still a draw."""
        board = RacingKingsBoard(setup="K6k/8/8/8/8/8/8/8 w - - 0 1")
        self.assertEqual(getStatus(board), (DRAW, DRAW_KINGSINEIGHTROW))

    def test_no_false_win_in_normal_play(self):
        """A normal mid-game position with no king on the back rank must stay
        RUNNING -- the fix must not fire prematurely."""
        board = RacingKingsBoard(setup="8/8/8/8/8/8/k6K/8 w - - 0 1")
        self.assertEqual(getStatus(board), (RUNNING, UNKNOWN_REASON))

    def test_sequence_reproduces_1889(self):
        """Reproduce #1889 as a move sequence: White races the king to the back
        rank, Black cannot also reach it and makes another king move, and it is
        White's turn again with the king already on the back rank -> White won."""
        # White king on h7, Black king on a1, White to move.
        board = RacingKingsBoard(setup="8/7K/8/8/8/8/k7/8 w - - 0 1")
        board = board.move(parseSAN(board, "Kh8"))  # White reaches back rank
        board = board.move(parseSAN(board, "Ka2"))  # Black cannot race there
        # White to move, own king already on the back rank -> game over.
        self.assertEqual(getStatus(board), (WHITEWON, WON_KINGINEIGHTROW))


if __name__ == "__main__":
    unittest.main()

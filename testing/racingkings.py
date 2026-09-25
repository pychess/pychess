import unittest

from pychess.Utils.const import (
    A8,
    BLACK,
    BLACKWON,
    DRAW,
    DRAW_KINGSINEIGHTROW,
    H8,
    RUNNING,
    UNKNOWN_REASON,
    WHITE,
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


# ---------------------------------------------------------------------------
# Real Racing Kings games pulled from the lichess.org game database
# (lichess_db_racingKings_rated_2026-08). Every move list is a genuine game that
# ended with a king reaching the back rank. They are replayed move by move and
# used to confirm getStatus() agrees with the real outcome.
#
# "type B" games are the interesting ones for issue #1889: the winner's king is
# already on the back rank and it is the *winner's* turn again (the loser could
# also have reached the back rank, so the game continued for one more move, but
# they failed to and now the win must stand). Before the fix getStatus() returned
# RUNNING for these instead of a win.
# ---------------------------------------------------------------------------

_REAL_RK_GAMES = [
    # type B (winner to move, own king already on the back rank) -- #1889 fix
    (["Bd4", "Rb8", "Bxa1", "Be4", "Kg3", "Ka3", "Kh4", "Kb4", "Kg5", "Ka5",
      "Kf6", "Bxg2", "Rxg2", "Ka6", "Rg7", "R1b7", "Rxb7", "Nc4", "Kf7", "Na5",
      "Rxb8", "Ka7", "Kf8", "Nc6"], "1-0"),
    (["Kh3", "Ka3", "Rg8", "Rb4", "R1g4", "Ka4", "Kh4", "Ka5", "Kh5", "Rb6",
      "R8g6", "Ka6", "Rg8", "Ka7", "R4g6", "Bb3", "Rxb6", "Bxg8", "Kh6", "Qa5",
      "Kg7", "Qxb6", "Kxg8", "Qxf2"], "1-0"),
    (["Kh3", "Rb8", "Kh4", "Ka3", "Kh5", "Ka4", "Rg8", "Ka5", "Kh6", "Ka6",
      "R1g7", "Nxf2", "Nxc2", "R1b7", "Rxb7", "Nxh1", "Rbxb8", "Ka7", "Kg6",
      "Qe5", "Kf7", "Qd6", "Ke8", "Bb2"], "1-0"),
    # type A (winner reached the back rank and the loser, to move, cannot also
    # reach it -> immediate win). Baseline coverage of the main win path.
    (["Kh3", "Rb8", "Kh4", "Ka3", "Kh5", "Ka4", "Kh6", "R8b7", "Rg7", "Qb2",
      "R1g6", "Rxg7", "Rxg7", "Qb7", "Nxc2", "Ka5", "Rxb7", "Rxb7", "Qxb7",
      "Nc3", "Kg7", "Nd5", "Kf8"], "1-0"),
    (["Kh3", "Ka3", "Kh4", "Ka4", "Rg5", "Rb6", "Kh5", "Qf6", "Bxb6", "Qxb6",
      "Nxc1", "Nxf1", "Nxc2", "Rb5", "Rxb5", "Nf2", "Rxb6", "Nxh1", "Kh6", "Ne3",
      "Kh7", "Nxc2", "Kh8"], "1-0"),
    (["Kh3", "Nxf1", "Kh4", "Nxf2", "Rxf2", "Rb7", "Nxc2", "R1b6", "Nxa1", "Ka3",
      "Nxc1", "Ka4", "Rf8", "Ka5", "Kh5", "Ka6", "Rg6", "Ka7", "Qxf1", "Rb8",
      "Rgg8", "Ka8"], "0-1"),
    (["Rg3", "Ne4", "Rg4", "Nexf2", "Qf3", "Be4", "Qxe4", "Nxe4", "Rxe4", "Ka3",
      "Kh3", "Rb4", "Re5", "Ka4", "Rg6", "Qxe5", "Rg4", "Ka5", "Kh4", "Ka6",
      "Rc4", "Ka7", "Rxb4", "Ka8"], "0-1"),
]

_EXPECTED_RK_RESULT = {
    "1-0": (WHITEWON, WON_KINGINEIGHTROW),
    "0-1": (BLACKWON, WON_KINGINEIGHTROW),
}


class RealRacingKingsGamesTestCase(unittest.TestCase):
    def _assert_rk_terminal(self, board):
        """A king on the back rank must end the game: a win for its owner, or a
        draw if both kings are there. It can never still be RUNNING. This is the
        invariant that issue #1889 broke (winner to move with its own king on the
        back rank returned RUNNING)."""
        lboard = board.board
        wk = lboard.kings[WHITE]
        bk = lboard.kings[BLACK]
        wk8 = A8 <= wk <= H8
        bk8 = A8 <= bk <= H8
        if wk8 and bk8:
            self.assertEqual(getStatus(board)[0], DRAW)
            return
        if wk8:
            self.assertEqual(getStatus(board), (WHITEWON, WON_KINGINEIGHTROW))
        elif bk8:
            self.assertEqual(getStatus(board), (BLACKWON, WON_KINGINEIGHTROW))

    def test_real_lichess_games(self):
        """Replay real Racing Kings games from lichess and confirm getStatus()
        matches the actual result at every position where a king is on the back
        rank, and at the final position."""
        for moves, result in _REAL_RK_GAMES:
            with self.subTest(result=result, first_move=moves[0]):
                board = RacingKingsBoard()
                for san in moves:
                    board = board.move(parseSAN(board, san))
                    self._assert_rk_terminal(board)
                self.assertEqual(getStatus(board), _EXPECTED_RK_RESULT[result])


if __name__ == "__main__":
    unittest.main()

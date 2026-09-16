import unittest

from pychess.Utils.const import (
    B2,
    BLACK,
    CAMBODIANCHESS,
    C3,
    D1,
    F2,
    H1,
    H8,
    KING,
    QUEEN,
    WHITE,
)
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import FCORD, TCORD
from pychess.Utils.lutils.lmovegen import genAllMoves, genPieceMoves
from pychess.Variants.asean import KAMBODIANSTART


def moves(board):
    return {(FCORD(move), TCORD(move)) for move in genAllMoves(board)}


class CambodianSpecialMovesTestCase(unittest.TestCase):
    def board(self, fen):
        board = LBoard(CAMBODIANCHESS)
        board.applyFen(fen)
        return board

    def test_starting_fen_enables_special_move_rights(self):
        board = self.board(KAMBODIANSTART)

        self.assertTrue(board.is_first_move[KING][WHITE])
        self.assertTrue(board.is_first_move[QUEEN][WHITE])
        self.assertTrue(board.is_first_move[KING][BLACK])
        self.assertTrue(board.is_first_move[QUEEN][BLACK])
        self.assertEqual(board.asFen().split()[2], "DEde")

    def test_special_move_rights_are_part_of_position_hash(self):
        with_rights = self.board(KAMBODIANSTART)
        without_rights = self.board(
            "rnsmksnr/8/pppppppp/8/8/PPPPPPPP/8/RNSKMSNR w - - 0 1"
        )

        self.assertNotEqual(with_rights.hash, without_rights.hash)
        self.assertNotEqual(with_rights, without_rights)

    def test_dash_fen_disables_special_move_rights(self):
        board = self.board("rnsmksnr/8/pppppppp/8/8/PPPPPPPP/8/RNSKMSNR w - - 0 1")

        self.assertFalse(board.is_first_move[KING][WHITE])
        self.assertFalse(board.is_first_move[QUEEN][WHITE])
        self.assertFalse(board.is_first_move[KING][BLACK])
        self.assertFalse(board.is_first_move[QUEEN][BLACK])
        self.assertEqual(board.asFen().split()[2], "-")

    def test_king_special_move_is_not_a_check_evasion(self):
        board = self.board("3rk3/8/8/8/8/8/8/3KM3 w DE - 0 1")

        self.assertTrue(board.isChecked())
        self.assertNotIn((D1, B2), moves(board))
        self.assertNotIn((D1, F2), moves(board))

    def test_rook_aiming_permanently_removes_king_special_move(self):
        board = self.board("4k2r/8/8/8/8/8/8/3KM3 b DE - 0 1")

        # h8-h1 aims along White's first rank. The queen on e1 remains between
        # rook and king, but Cambodian rules still remove the king's leap right.
        rook_move = next(
            move
            for move in genAllMoves(board)
            if FCORD(move) == H8 and TCORD(move) == H1
        )
        board.applyMove(rook_move)

        self.assertFalse(board.is_first_move[KING][WHITE])
        self.assertTrue(board.is_first_move[QUEEN][WHITE])
        self.assertEqual(board.asFen().split()[2], "E")

        board.popMove()
        self.assertTrue(board.is_first_move[KING][WHITE])
        self.assertTrue(board.is_first_move[QUEEN][WHITE])
        self.assertEqual(board.asFen().split()[2], "DE")

    def test_queen_piece_lookup_only_returns_requested_destination(self):
        board = self.board("4k3/8/8/8/8/2M5/8/3KM3 w E - 0 1")

        queen_moves = genPieceMoves(board, QUEEN, B2)

        self.assertEqual(len(queen_moves), 1)
        move = queen_moves.pop()
        self.assertEqual(FCORD(move), C3)
        self.assertEqual(TCORD(move), B2)

    def test_capturing_virgin_queen_removes_its_special_move_right(self):
        board = self.board("4k3/8/8/8/8/5n2/8/3KM3 b DE - 0 1")
        queen_capture = next(
            move
            for move in genAllMoves(board)
            if TCORD(move) == board.ini_queens[WHITE]
        )

        board.applyMove(queen_capture)

        self.assertTrue(board.is_first_move[KING][WHITE])
        self.assertFalse(board.is_first_move[QUEEN][WHITE])
        self.assertEqual(board.asFen().split()[2], "D")

        board.popMove()
        self.assertTrue(board.is_first_move[QUEEN][WHITE])
        self.assertEqual(board.asFen().split()[2], "DE")

    def test_right_requires_piece_on_initial_square(self):
        board = self.board("4k3/8/8/8/8/8/4M3/3K4 w DE - 0 1")

        self.assertTrue(board.is_first_move[KING][WHITE])
        self.assertFalse(board.is_first_move[QUEEN][WHITE])
        self.assertEqual(board.asFen().split()[2], "D")

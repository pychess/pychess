import unittest

from pychess.Utils.const import (
    A1,
    A8,
    C1,
    C8,
    E1,
    E8,
    G1,
    G8,
    H1,
    H8,
    FISCHERRANDOMCHESS,
    KING_CASTLE,
    QUEEN_CASTLE,
    SETUPCHESS,
    W_OO,
    W_OOO,
    B_OO,
    B_OOO,
)
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import parseAN
from pychess.Utils.lutils.lmovegen import genCastles, newMove

# TODO: add more test data
data = (
    (
        "r3k2r/8/8/8/8/8/8/R3K2R w AH - 0 1",
        [(E1, H1, KING_CASTLE), (E1, A1, QUEEN_CASTLE)],
    ),
    (
        "r3k2r/8/8/8/8/8/8/R3K2R b ah - 0 1",
        [(E8, H8, KING_CASTLE), (E8, A8, QUEEN_CASTLE)],
    ),
    (
        "1br3kr/2p5/8/8/8/8/8/1BR3KR w CH - 0 2",
        [(G1, H1, KING_CASTLE), (G1, C1, QUEEN_CASTLE)],
    ),
    (
        "1br3kr/2p5/8/8/8/8/8/1BR3KR b ch - 0 2",
        [(G8, H8, KING_CASTLE), (G8, C8, QUEEN_CASTLE)],
    ),
    ("2r1k2r/8/8/8/8/8/8/2R1K2R w H - 0 1", [(E1, H1, KING_CASTLE)]),
    ("2r1k2r/8/8/8/8/8/8/2R1K2R b h - 0 1", [(E8, H8, KING_CASTLE)]),
    ("3rk1qr/8/8/8/8/8/8/3RK1QR w - - 0 1", []),
    ("3rk1qr/8/8/8/8/8/8/3RK1QR b - - 0 1", []),
)


class FRCCastlingTestCase(unittest.TestCase):
    def testFRCCastling(self):
        """Testing FRC castling movegen"""
        print()

        for fen, castles in data:
            print(fen)
            board = LBoard(FISCHERRANDOMCHESS)
            board.applyFen(fen)
            # print board
            moves = [move for move in genCastles(board)]
            self.assertEqual(len(moves), len(castles))
            for i, castle in enumerate(castles):
                kfrom, kto, flag = castle
                self.assertEqual(moves[i], newMove(kfrom, kto, flag))

    def testFRCCastlingUCI(self):
        """Testing UCI engine FRC castling move"""
        print()

        fen = "rbq1krb1/pp1pp1pp/2p1n3/5p2/2PP1P1n/4B1N1/PP2P1PP/RBQNKR2 w FAfa - 2 6"
        print(fen)
        board = LBoard(FISCHERRANDOMCHESS)
        board.applyFen(fen)
        # print board
        moves = [move for move in genCastles(board)]
        self.assertTrue(parseAN(board, "e1g1") in moves)


# (FEN, expected castling flags) for X-FEN file-letter rights parsed as SETUPCHESS.
# This mirrors how the Setup Position dialog re-parses a loaded Chess960 position.
setup_data = (
    (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w AHah - 0 1",
        W_OO | W_OOO | B_OO | B_OOO,
    ),
    ("1br3kr/2p5/8/8/8/8/8/1BR3KR w CH - 0 2", W_OO | W_OOO),
    ("1br3kr/2p5/8/8/8/8/8/1BR3KR b ch - 0 2", B_OO | B_OOO),
    ("2r1k2r/8/8/8/8/8/8/2R1K2R w H - 0 1", W_OO),
    ("2r1k2r/8/8/8/8/8/8/2R1K2R b h - 0 1", B_OO),
    (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        W_OO | W_OOO | B_OO | B_OOO,
    ),
    ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1", 0),
)


class SetupCastlingTestCase(unittest.TestCase):
    def testSetupFileLetterCastling(self):
        """Testing SETUPCHESS X-FEN file-letter castling parsing"""
        for fen, expected in setup_data:
            board = LBoard(SETUPCHESS)
            board.applyFen(fen)
            self.assertEqual(board.castling, expected, fen)


# (piece placement, ticked castling flags, expected castling field) for the
# Setup Position dialog's FRC castling helper. The adversarial cases ensure a
# right ticked without a matching rook (or king) is dropped instead of crashing
# with reprCord[None] in reprCastling().
dialog_data = (
    # Happy path: standard back rank, all four rights ticked.
    (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
        (W_OO, W_OOO, B_OO, B_OOO),
        "HAha",
    ),
    # Kingside ticked but no rook to the right of the king -> dropped.
    ("4k3/8/8/8/8/8/8/R3K3", (W_OO,), "-"),
    # Both white rights ticked but the white king is missing -> dropped.
    ("4k3/8/8/8/8/8/8/R6R", (W_OO, W_OOO), "-"),
    # White king off the back rank (on e2) -> back-rank rooks ignored, dropped.
    ("4k3/8/8/8/8/8/4K3/R6R", (W_OO, W_OOO), "-"),
    # Queenside ticked but the only left-of-king rook is the opponent's -> dropped.
    ("4k3/8/8/8/8/8/8/r3K2R", (W_OOO,), "-"),
    # Same position: kingside white rook (h1) is valid and emitted.
    ("4k3/8/8/8/8/8/8/r3K2R", (W_OO,), "H"),
)


class DialogFRCCastlingFieldTestCase(unittest.TestCase):
    def testCastlingFieldGuards(self):
        """Testing Setup dialog _castling_field FRC guards against missing rook/king"""
        from pychess.widgets.newGameDialog import SetupPositionExtension

        for pieces, flags, expected in dialog_data:
            SetupPositionExtension.castl = set(flags)
            result = SetupPositionExtension._castling_field(FISCHERRANDOMCHESS, pieces)
            self.assertEqual(result, expected, pieces)


if __name__ == "__main__":
    unittest.main()

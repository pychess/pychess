import unittest

from pychess.Utils.const import SCHESS, A1, C1, E1, H1, G1, F3, BLACK, WHITE, ROOK, HAWK, ELEPHANT, \
    HAWK_GATE, ELEPHANT_GATE, HAWK_GATE_AT_ROOK, ELEPHANT_GATE_AT_ROOK, QUEEN_CASTLE
from pychess.Utils import Move
from pychess.Utils.lutils.bitboard import toString
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.ldata import brank8
from pychess.Utils.lutils.lmove import parseAN, toAN, parseSAN, toSAN
from pychess.Utils.lutils.lmovegen import genAllMoves, newMove
from pychess.Variants.seirawan import SCHESSSTART, SchessBoard


def placement(fen):
    return fen.split()[0]


class SchessTestCase(unittest.TestCase):
    def test_moves_from_startpos(self):
        board = LBoard(SCHESS)
        board.applyFen(SCHESSSTART)

        moves = set()
        for move in genAllMoves(board):
            moves.add(toAN(board, move))

            board.applyMove(move)
            board.popMove()
            self.assertEqual(placement(board.asFen()), placement(SCHESSSTART))

        self.assertIn("b1a3e", moves)
        self.assertIn("b1a3h", moves)
        self.assertIn("b1c3e", moves)
        self.assertIn("b1c3h", moves)

        self.assertIn("g1f3e", moves)
        self.assertIn("g1f3h", moves)
        self.assertIn("g1h3e", moves)
        self.assertIn("g1h3h", moves)

    def test_promotion(self):
        # promotion moves
        FEN = "r4knr/1bpp1Pp1/pp3b2/q2pep1p/3N4/P1N5/1PPQBPPP/R1B1K2R[hHE] w KQ - 1 17"
        board = LBoard(SCHESS)
        board.applyFen(FEN)
        print("--------")
        print(board)

        moves = set()
        for move in genAllMoves(board):
            moves.add(toAN(board, move))

        self.assertIn("f7g8=H", moves)
        self.assertIn("f7g8=E", moves)

    def test_board(self):
        FEN = "r2qk2r/pppbbppp/4pn2/1N1p4/1n1P4/4PN2/PPPBBPPP/R2QK2R[heHE] w KQkq - 10 8"
        board = SchessBoard(setup=FEN)
        # print("--------")
        # print(board)
        self.assertEqual(board.data[0][7].color, WHITE)
        self.assertEqual(board.data[0][7].piece, ROOK)

        board = board.move(Move.Move(parseSAN(board.board, 'O-O/Hh1')))
        # board.printPieces()

        self.assertEqual(board.data[0][7].color, WHITE)
        self.assertEqual(board.data[0][7].piece, HAWK)

        moves = "c3 c5 e3 d5 Nf3/E Nc6/H d4 e5 Nxe5 Nxe5 dxe5 Hxe5 e4 Nf6 Bf4/H Hc6 e5 Nd7 Be2 Nxe5 Bxe5 Hxe5 Bb5+ Bd7 Ee2 Bd6 Exe5+ Bxe5 Bxd7+ Qxd7/E"
        board = SchessBoard(setup=SCHESSSTART)
        for san in moves.split():
            move = parseSAN(board.board, san)
            board = board.move(Move.Move(move))
            # print(san)
            # board.printPieces()

        self.assertEqual(board.data[7][3].color, BLACK)
        self.assertEqual(board.data[7][3].piece, ELEPHANT)

    def test_gating_san_move(self):
        board = LBoard(SCHESS)
        board.applyFen(SCHESSSTART)

        self.assertEqual(repr(Move.Move(parseSAN(board, 'Nf3/H'))), 'g1f3h')
        self.assertEqual(repr(Move.Move(parseSAN(board, 'Nf3/E'))), 'g1f3e')

        self.assertEqual(toSAN(board, newMove(G1, F3, HAWK_GATE)), "Nf3/H")
        self.assertEqual(toSAN(board, newMove(G1, F3, ELEPHANT_GATE)), "Nf3/E")

    def test_gating_king_move(self):
        board = LBoard(SCHESS)
        board.applyFen(SCHESSSTART)

        for move in "e2e3 e7e5 d1h5 d8e7 h5g4 b8c6 g1f3 d7d5 g4h4 e7c5 h4a4 e5e4 d2d4 c5e7 f3d2 e7b4 a4b4 c6b4".split():
            board.applyMove(parseAN(board, move))
        print("--------")
        print(board)

        moves = set()
        for move in genAllMoves(board):
            moves.add(toAN(board, move))

        self.assertIn("e1d1e", moves)
        self.assertIn("e1d1h", moves)

        fen = board.asFen()
        move = parseAN(board, "e1d1e")
        board.applyMove(move)
        print("e1d1e")
        print(board)

        self.assertEqual(placement(board.asFen()), "r1b1kbnr/ppp2ppp/8/3p4/1n1Pp3/4P3/PPPN1PPP/RNBKEB1R[heH]")

        board.popMove()
        self.assertEqual(placement(board.asFen()), placement(fen))

    def test_gating_castle_at_rook_wOOO(self):
        board = LBoard(SCHESS)
        board.applyFen(SCHESSSTART)

        for move in "e2e4 d7d6 d1e2 c8d7 g1f3 g8f6 e4e5 f6d5 e2e4 d5b6 d2d3 d7c6 e4f5 c6d7 f5g5 g7g6 f3d4 h7h5 g5f4 d6e5 f4h4 f8g7 d4f3 d7g4 b1c3 f7f6 c3e4 d8d5 e4c3 d5c5 c1e3 c5d6 h2h3 g4f3 g2f3 e8g8h".split():
            board.applyMove(parseAN(board, move))

        moves = set()
        for move in genAllMoves(board):
            moves.add(toAN(board, move))
        print("--------")
        print(board)

        self.assertIn("a1e1h", moves)
        self.assertIn("a1e1e", moves)

        fen = board.asFen()
        parseAN(board, "a1e1e")
        board.applyMove(move)
        print("a1e1e")
        print(board)

        self.assertEqual(placement(board.asFen()), "rn2hrk1/ppp1p1b1/1n1q1pp1/4p2p/7Q/2NPBP1P/PPP2P2/E1KR1B1R[eH]")

        board.popMove()
        self.assertEqual(placement(board.asFen()), placement(fen))

    def test_gating_castle_at_rook_bOO(self):
        board = LBoard(SCHESS)
        board.applyFen(SCHESSSTART)

        for move in "e2e3 e7e6 g1f3 c7c6 c2c3 d7d5 d2d4 g8f6 h2h3 f6e4 d1c2 b8d7 f1d3 f7f5 e1g1e d8c7 e1e2 f8e7 c2d1".split():
            board.applyMove(parseAN(board, move))

        moves = set()
        for move in genAllMoves(board):
            moves.add(toAN(board, move))
        print("--------")
        print(board)

        self.assertIn("h8e8h", moves)
        self.assertIn("h8e8e", moves)

        fen = board.asFen()
        move = parseAN(board, "h8e8h")
        board.applyMove(move)
        print("h8e8e")
        print(board)

        self.assertEqual(placement(board.asFen()), "r1b2rkh/ppqnb1pp/2p1p3/3p1p2/3Pn3/2PBPN1P/PP2EPP1/RNBQ1RK1[eH]")

        board.popMove()
        self.assertEqual(placement(board.asFen()), placement(fen))

    def test_gating_castle_at_rook_wOO(self):
        FEN = "r2qk2r/pppbbppp/4pn2/1N1p4/1n1P4/4PN2/PPPBBPPP/R2QK2R[heHE] w KQkq - 10 8"
        board = LBoard(SCHESS)
        board.applyFen(FEN)

        moves = set()
        for move in genAllMoves(board):
            moves.add(toAN(board, move))
        print("--------")
        print(board)

        self.assertIn("h1e1h", moves)
        self.assertIn("h1e1e", moves)

        self.assertEqual(repr(Move.Move(parseSAN(board, 'O-O/Hh1'))), 'h1e1h')
        self.assertEqual(repr(Move.Move(parseSAN(board, 'O-O/Eh1'))), 'h1e1e')

        self.assertEqual(toSAN(board, newMove(H1, E1, HAWK_GATE_AT_ROOK)), "O-O/Hh1")
        self.assertEqual(toSAN(board, newMove(H1, E1, ELEPHANT_GATE_AT_ROOK)), "O-O/Eh1")

        fen = board.asFen()
        move = parseAN(board, "h1e1e")
        board.applyMove(move)
        print("h1e1e")
        print(board)

        self.assertEqual(placement(board.asFen()), "r2qk2r/pppbbppp/4pn2/1N1p4/1n1P4/4PN2/PPPBBPPP/R2Q1RKE[heH]")

        board.popMove()
        self.assertEqual(placement(board.asFen()), placement(fen))

    def test_disambig_gating_san(self):
        FEN = "rnbqkb1r/ppp1pppp/3p1n2/8/2PP4/2N5/PP2PPPP/RHBQKBNR[Eeh] b KQACDEFGHkqabcdefh - 1 3"
        board = LBoard(SCHESS)
        board.applyFen(FEN)

        moves = set()
        for move in genAllMoves(board):
            moves.add(toAN(board, move))
        print("--------")
        print(board)

        self.assertIn("f6d7", moves)
        self.assertNotIn("f6d7/H", moves)
        self.assertNotIn("f6d7/E", moves)
        self.assertIn("b8d7", moves)
        self.assertIn("b8d7h", moves)
        self.assertIn("b8d7e", moves)

        self.assertEqual(repr(Move.Move(parseSAN(board, 'Nfd7'))), 'f6d7')
        self.assertEqual(repr(Move.Move(parseSAN(board, 'Nbd7'))), 'b8d7')
        self.assertEqual(repr(Move.Move(parseSAN(board, 'Nbd7/H'))), 'b8d7h')
        self.assertEqual(repr(Move.Move(parseSAN(board, 'Nbd7/E'))), 'b8d7e')

    def test_default_gating_avail(self):
        board = LBoard(SCHESS)
        board.applyFen(SCHESSSTART)

        print(board)
        print(toString(board.virgin[0]))
        print(toString(board.virgin[1]))

        self.assertEqual(board.virgin[0], brank8[1])
        self.assertEqual(board.virgin[1], brank8[0])

        board = LBoard(SCHESS)
        FEN = "r1hqerk1/pp1nbppp/2pp1nb1/4p3/2PPP3/2N1B1PP/PP2NPB1/RH1QK2R/E w KQHEDA - 2 10"
        board.applyFen(FEN)
        print("-----------")
        print(board)

        move = parseSAN(board, "O-O")
        board.applyMove(move)
        castl = board.asFen().split()[2]

        self.assertNotIn("Q", castl)
        self.assertNotIn("K", castl)
        self.assertNotIn("E", castl)
        self.assertNotIn("H", castl)

    def test_gating_castle_at_rook_wOOO_SAN(self):
        FEN = "r2ek2r/5pp1/1pp1pnp1/2pp1h2/3P4/2P1PP2/PP1N2PP/R3K1HR/E w KQHEAkq - 2 16"
        board = LBoard(SCHESS)
        board.applyFen(FEN)

        self.assertEqual(repr(Move.Move(parseSAN(board, 'O-O-O'))), 'e1c1')
        self.assertEqual(repr(Move.Move(parseSAN(board, 'O-O-O/Ea1'))), 'a1e1e')
        self.assertEqual(repr(Move.Move(parseSAN(board, 'O-O-O/Ee1'))), 'e1c1e')

        self.assertEqual(toSAN(board, newMove(E1, C1, QUEEN_CASTLE)), "O-O-O")
        self.assertEqual(toSAN(board, newMove(A1, E1, ELEPHANT_GATE_AT_ROOK)), "O-O-O/Ea1")
        self.assertEqual(toSAN(board, newMove(E1, C1, ELEPHANT_GATE)), "O-O-O/Ee1")


if __name__ == '__main__':
    unittest.main()

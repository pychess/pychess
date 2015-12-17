# -*- coding: UTF-8 -*-

from __future__ import print_function

import sys
import unittest

from pychess.Utils.const import *
from pychess.Utils.logic import validate, getStatus
from pychess.Utils.Move import Move, parseSAN
from pychess.Variants.atomic import AtomicBoard
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmovegen import genAllMoves

# ♜ . . ♞ ♚ ♝ ♞ ♜
# ♟ ♟ . ♝ ♟ ♟ ♟ ♟
# . . ♟ . . . . .
# . ♘ . . . . . .
# . . . ♛ . . . .
# . . . . . . . .
# ♙ ♙ ♙ ♙ . ♙ ♙ ♙
# ♖ . ♗ ♕ ♔ ♗ . ♖
FEN1 = "r2nkbnr/pp1bpppp/2p5/1N6/3q4/8/PPPP1PPP/R1BQKB1R w KQkq - 0 1"

FEN2 = "8/8/8/8/5k2/8/1qK5/8 b - - 0 1"

FEN3 = "7k/6R1/8/5K2/8/8/8/8 b - - 0 1"

FEN4 = "r4bn1/4p2r/2n2pp1/p2p2Pk/1p4Qp/2P1P3/PP1P3P/R1B1K2R b KQ - 0 1"


class AtomicTestCase(unittest.TestCase):
    def test_validate1(self):
        """Testing castling rights lose in explosion in Atomic variant"""
        
        board = AtomicBoard(setup=FEN1)
        board = board.move(parseSAN(board, 'Nxa7'))
        print(board)
        # Rook exploded, no O-O-O anymore!
        self.assertTrue(validate(board, parseSAN(board, 'b6')))
        self.assertTrue(not validate(board, parseSAN(board, 'a6')))
        self.assertTrue(not validate(board, parseSAN(board, 'Rb8')))
        self.assertTrue(not validate(board, parseSAN(board, 'O-O-O')))

    def test_validate2(self):
        """Testing explode king vs mate in Atomic variant"""
        
        board = AtomicBoard(setup=FEN1)
        board = board.move(parseSAN(board, 'Nc7+'))
        print(board)
        # King explosion takes precedence over mate!
        self.assertTrue(validate(board, parseSAN(board, 'Qxd2')))
        self.assertTrue(validate(board, parseSAN(board, 'Qxf2')))
        self.assertTrue(not validate(board, parseSAN(board, 'Qxb2')))
        self.assertTrue(not validate(board, parseSAN(board, 'Qe4+')))

    def test_getstatus1(self):
        """Testing bare black king is not draw in Atomic variant"""
        
        board = AtomicBoard(setup=FEN2)
        board = board.move(parseSAN(board, 'Qxc2'))
        print(board)
        self.assertEqual(getStatus(board), (BLACKWON, WON_KINGEXPLODE))

    def test_getstatus2(self):
        """Testing bare white king is not draw in Atomic variant"""

        board = AtomicBoard(setup=FEN3)
        self.assertTrue(not validate(board, parseSAN(board, 'Kxg7')))
        self.assertTrue(not validate(board, parseSAN(board, 'Kg8')))
        self.assertTrue(not validate(board, parseSAN(board, 'Kh7')))
        print(board)
        self.assertEqual(getStatus(board), (DRAW, DRAW_STALEMATE))

    def test_getstatus3(self):
        """Testing possible to mate with the queen unaided in Atomic variant"""
        
        board = AtomicBoard(setup=FEN4)
        print(board)
        self.assertEqual(getStatus(board), (WHITEWON, WON_MATE))

    def test_apply_pop(self):
        """Testing Atomic applyMove popMove"""

        board = LBoard(variant=ATOMICCHESS)
        board.applyFen(FEN1)
        print(board)
        hist_exploding_around0 = [a[:] for a in board.hist_exploding_around]
        print_apply_pop = False

        for lmove1 in genAllMoves(board):
            board.applyMove(lmove1)
            if board.opIsChecked():
                if print_apply_pop: print("popMove1 (invalid)", Move(lmove1))
                board.popMove()
                continue
                
            hist_exploding_around1 = [a[:] for a in board.hist_exploding_around]
            for lmove2 in genAllMoves(board):
                board.applyMove(lmove2)
                if print_apply_pop: print("   applyMove2", Move(lmove2))
                if board.opIsChecked():
                    if print_apply_pop: print("   popMove2 (invalid)", Move(lmove2))
                    board.popMove()
                    continue

                hist_exploding_around2 = [a[:] for a in board.hist_exploding_around]
                for lmove3 in genAllMoves(board):
                    board.applyMove(lmove3)
                    if print_apply_pop: print("      applyMove3", Move(lmove3))
                    if board.opIsChecked():
                        if print_apply_pop: print("      popMove3 (invalid)", Move(lmove3))
                        board.popMove()
                        continue

                    board.popMove()
                    if print_apply_pop: print("      popMove3", Move(lmove3))

                    self.assertEqual(hist_exploding_around2, board.hist_exploding_around)

                board.popMove()
                if print_apply_pop: print("   popMove2", Move(lmove2))

                self.assertEqual(hist_exploding_around1, board.hist_exploding_around)
                
            board.popMove()
            if print_apply_pop: print("popMove1", Move(lmove1))

            self.assertEqual(hist_exploding_around0, board.hist_exploding_around)

if __name__ == '__main__':
    unittest.main()

from __future__ import print_function
# -*- coding: UTF-8 -*-

import sys
import unittest

from pychess.Utils.const import ATOMICCHESS
from pychess.Utils.logic import validate
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
FEN = "r2nkbnr/pp1bpppp/2p5/1N6/3q4/8/PPPP1PPP/R1BQKB1R w KQkq - 0 1"

class AtomicTestCase(unittest.TestCase):
    def test_validate1(self):
        """Testing castling rights lose in explosion in Atomic variant"""
        
        board = AtomicBoard(setup=FEN)
        board = board.move(parseSAN(board, 'Nxa7'))
        print(board)
        # Rook exploded, no O-O-O anymore!
        self.assertTrue(validate(board, parseSAN(board, 'b6')))
        self.assertTrue(not validate(board, parseSAN(board, 'a6')))
        self.assertTrue(not validate(board, parseSAN(board, 'Rb8')))
        self.assertTrue(not validate(board, parseSAN(board, 'O-O-O')))

    def test_validate2(self):
        """Testing explode king vs mate in Atomic variant"""
        
        board = AtomicBoard(setup=FEN)
        board = board.move(parseSAN(board, 'Nc7+'))
        print(board)
        # King explosion takes precedence over mate!
        self.assertTrue(validate(board, parseSAN(board, 'Qxd2')))
        self.assertTrue(validate(board, parseSAN(board, 'Qxf2')))
        self.assertTrue(not validate(board, parseSAN(board, 'Qxb2')))
        self.assertTrue(not validate(board, parseSAN(board, 'Qe4+')))

    def test_apply_pop(self):
        """Testing Atomic applyMove popMove"""

        board = LBoard(variant=ATOMICCHESS)
        board.applyFen(FEN)
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

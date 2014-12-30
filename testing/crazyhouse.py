# -*- coding: UTF-8 -*-

from __future__ import print_function

import sys
import unittest

from pychess.Utils.logic import validate
from pychess.Utils.Move import Move, parseSAN
from pychess.Variants.crazyhouse import CrazyhouseBoard
from pychess.Utils.lutils.lmovegen import genAllMoves
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.const import CRAZYHOUSECHESS


# Black has a pawn and a rook in hes holding
# ♚ . ♖ ♔ . . . . 
# . . . . . . . . 
# . . . . . . . . 
# . . . . . . . . 
# . . . . . . . . 
# . . . . . . . . 
# . . . . . . . . ♟ ♜
FEN0 = "k1RK4/8/8/8/8/8/8/8/pr b - - 0 1"

# ♜ ♞ ♝ ♛ ♚ ♝ ♖ ♜
# ♟ ♙ ♙ ♟ ♟ ♘ ♟ ♟
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# ♙ ♙ ♙ ♙ ♙ ♙ ♙ ♙
# ♖ ♘ ♗ ♕ ♔ ♗ ♘ ♖
FEN1 = "rnbqkbRr/pPPppNpp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

class CrazyhouseTestCase(unittest.TestCase):
    def test_validate(self):
        """Testing validate move in Crazyhouse variant"""
        
        board = CrazyhouseBoard(setup=FEN0)
        print(board)
        # Drop can save mate
        self.assertTrue(validate(board, parseSAN(board, 'R@b8')))
        self.assertTrue(validate(board, parseSAN(board, 'Ka7')))
        self.assertTrue(validate(board, parseSAN(board, 'Kb7')))
        self.assertTrue(not validate(board, parseSAN(board, 'P@b8')))
        self.assertTrue(not validate(board, parseSAN(board, 'Kb8')))

    def test_apply_pop(self):
        """Testing Crazyhouse applyMove popMove"""

        board = LBoard(variant=CRAZYHOUSECHESS)
        board.applyFen(FEN1)
        
        holding0 = (board.holding[0].copy(), board.holding[1].copy())
        promoted0 = board.promoted[:]
        capture_promoting0 = board.capture_promoting
        hist_capture_promoting0 = board.hist_capture_promoting[:]

        print_board_promoted = False
        print_apply_pop = False

        for lmove1 in genAllMoves(board):
            #if lmove1 != parseAN(board, "c7b8=Q"):
            #    continue
            board.applyMove(lmove1)
            if print_apply_pop: print("applyMove1", Move(lmove1), board.holding, board.capture_promoting)
            if print_board_promoted: print(board.promoted)
            if board.opIsChecked():
                if print_apply_pop: print("popMove1 (invalid)", Move(lmove1))
                board.popMove()
                continue
                
            holding1 = (board.holding[0].copy(), board.holding[1].copy())
            promoted1 = board.promoted[:]
            capture_promoting1 = board.capture_promoting
            hist_capture_promoting1 = board.hist_capture_promoting[:]
            for lmove2 in genAllMoves(board):
                #if lmove2 != parseAN(board, "e8f7"):
                #   continue
                board.applyMove(lmove2)
                if print_apply_pop: print("   applyMove2", Move(lmove2), board.holding, board.capture_promoting)
                if print_board_promoted: print(board.promoted)
                if board.opIsChecked():
                    if print_apply_pop: print("   popMove2 (invalid)", Move(lmove2))
                    board.popMove()
                    continue

                holding2 = (board.holding[0].copy(), board.holding[1].copy())
                promoted2 = board.promoted[:]
                capture_promoting2 = board.capture_promoting
                hist_capture_promoting2 = board.hist_capture_promoting[:]
                for lmove3 in genAllMoves(board):
                    #if lmove3 != parseAN(board, "b8c8"):
                    #   continue
                    board.applyMove(lmove3)
                    if print_apply_pop: print("      applyMove3", Move(lmove3), board.holding, board.capture_promoting)
                    if print_board_promoted: print(board.promoted)
                    if board.opIsChecked():
                        if print_apply_pop: print("      popMove3 (invalid)", Move(lmove3))
                        board.popMove()
                        continue

                    board.popMove()
                    if print_apply_pop: print("      popMove3", Move(lmove3), board.holding, board.capture_promoting)
                    if print_board_promoted: print(board.promoted)

                    self.assertEqual(holding2, board.holding)
                    self.assertEqual(promoted2, board.promoted)
                    self.assertEqual(capture_promoting2, board.capture_promoting)
                    self.assertEqual(hist_capture_promoting2, board.hist_capture_promoting)

                board.popMove()
                if print_apply_pop: print("   popMove2", Move(lmove2), board.holding, board.capture_promoting)
                if print_board_promoted: print(board.promoted)

                self.assertEqual(holding1, board.holding)
                self.assertEqual(promoted1, board.promoted)
                self.assertEqual(capture_promoting1, board.capture_promoting)
                self.assertEqual(hist_capture_promoting1, board.hist_capture_promoting)
                
            board.popMove()
            if print_apply_pop: print("popMove1", Move(lmove1), board.holding, board.capture_promoting)
            if print_board_promoted: print(board.promoted)

            self.assertEqual(holding0, board.holding)
            self.assertEqual(promoted0, board.promoted)
            self.assertEqual(capture_promoting0, board.capture_promoting)
            self.assertEqual(hist_capture_promoting0, board.hist_capture_promoting)

if __name__ == '__main__':
    unittest.main()

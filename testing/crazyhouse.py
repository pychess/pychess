import sys
import unittest

from pychess.Utils.Move import Move
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmovegen import genAllMoves
from pychess.Utils.lutils.lmove import parseAN
from pychess.Utils.const import *


class CrazyhouseTestCase(unittest.TestCase):
    
    def test_apply_pop(self):
        """Testing Crazyhouse applyMove popMove"""

        board = LBoard(variant=CRAZYHOUSECHESS)
        board.applyFen("rnbqkbRr/pPPppNpp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        
        holding0 = [board.holding[0].copy(), board.holding[1].copy()]
        promoted0 = board.promoted[:]
        capture_promoting0 = board.capture_promoting
        hist_capture_promoting0 = board.hist_capture_promoting[:]

        for lmove1 in genAllMoves(board):
            board.applyMove(lmove1)
            if board.opIsChecked():
                board.popMove()
                continue
                
            holding1 = [board.holding[0].copy(), board.holding[1].copy()]
            promoted1 = board.promoted[:]
            capture_promoting1 = board.capture_promoting
            hist_capture_promoting1 = board.hist_capture_promoting[:]
            for lmove2 in genAllMoves(board):
                board.applyMove(lmove2)
                if board.opIsChecked():
                    board.popMove()
                    continue

                board.popMove()

                self.assertEqual(holding1, board.holding)
                self.assertEqual(promoted1, board.promoted)
                self.assertEqual(capture_promoting1, board.capture_promoting)
                self.assertEqual(hist_capture_promoting1, board.hist_capture_promoting)
                
            board.popMove()

            self.assertEqual(holding0, board.holding)
            self.assertEqual(promoted0, board.promoted)
            self.assertEqual(capture_promoting0, board.capture_promoting)
            self.assertEqual(hist_capture_promoting0, board.hist_capture_promoting)

if __name__ == '__main__':
    unittest.main()

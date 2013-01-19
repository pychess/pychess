import sys
import unittest

from pychess.Utils.Move import Move
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmovegen import genAllMoves
from pychess.Utils.const import *


class LBoardTestCase(unittest.TestCase):
    
    def test_apply_pop(self):
        """Testing apply pop move"""

        board = LBoard(variant=CRAZYHOUSECHESS)
        board.applyFen("rnbqkbRr/pPPppNpp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        board.holding[WHITE] = {PAWN:1, KNIGHT:1, BISHOP:1, ROOK:1, QUEEN:1}
        
        holding = [board.holding[0].copy(), board.holding[1].copy()]
        promoted = board.promoted[:]
        capture_promoting = board.capture_promoting
        hist_capture_promoting = board.hist_capture_promoting[:]

        for lmove in genAllMoves(board):
            #print "applyMove", Move(lmove)
            board.applyMove(lmove)
            if board.opIsChecked():
                #print "popMove", Move(lmove)
                board.popMove()
                continue
            #print "popMove", Move(lmove)
            board.popMove()

            self.assertEqual(holding, board.holding)
            self.assertEqual(promoted, board.promoted)
            self.assertEqual(capture_promoting, board.capture_promoting)
            self.assertEqual(hist_capture_promoting, board.hist_capture_promoting)

if __name__ == '__main__':
    unittest.main()

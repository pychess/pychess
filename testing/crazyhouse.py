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
        board.holding[WHITE] = {PAWN:1, KNIGHT:1, BISHOP:1, ROOK:1, QUEEN:1}
        
        holding = [board.holding[0].copy(), board.holding[1].copy()]
        promoted = board.promoted[:]
        capture_promoting = board.capture_promoting
        hist_capture_promoting = board.hist_capture_promoting[:]

        for lmove1 in genAllMoves(board):
            #if lmove1 != parseAN(board, "c7b8=Q"):
            #    continue
            #print "applyMove1", Move(lmove1)
            board.applyMove(lmove1)
            if board.opIsChecked():
                #print "popMove1 (invalid)", Move(lmove1)
                board.popMove()
                continue
                
            for lmove2 in genAllMoves(board):
                #if lmove2 != parseAN(board, "a8b8"):
                #    continue
                #print "   applyMove2", Move(lmove2)
                board.applyMove(lmove2)
                if board.opIsChecked():
                    #print "   popMove2 (invalid)", Move(lmove2)
                    board.popMove()
                    continue

                #print "   popMove2", Move(lmove2)
                board.popMove()
                
            #print "popMove1", Move(lmove1)
            board.popMove()

            self.assertEqual(holding, board.holding)
            self.assertEqual(promoted, board.promoted)
            self.assertEqual(capture_promoting, board.capture_promoting)
            self.assertEqual(hist_capture_promoting, board.hist_capture_promoting)

if __name__ == '__main__':
    unittest.main()

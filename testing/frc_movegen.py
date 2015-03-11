from __future__ import print_function
import unittest

from pychess.Utils.lutils.lmovegen import genAllMoves, genCheckEvasions
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.bitboard import toString, iterBits
from pychess.Utils.lutils.ldata import *
from pychess.Utils.lutils.validator import validateMove

from pychess.Utils.lutils.lmove import toSAN, toAN, parseSAN, ParsingError
from pychess.Utils.const import *


class FRCFindMovesTestCase(unittest.TestCase):
    """Move generator test using perftsuite.epd from
       http://www.albert.nu/programs/sharper/perft.htm"""

    MAXDEPTH = 0
    
    def perft(self, board, depth, prevmoves):
        if depth == 0:
            self.count += 1
            return
        
        for move in genAllMoves(board):
            board.applyMove(move)
            if board.opIsChecked():
                board.popMove()
                continue

            # Validator test
            board.popMove()
            self.assertTrue(validateMove(board, move))

            board.applyMove (move)
            self.perft(board, depth-1, prevmoves)
            board.popMove()
    
    def setUp(self):
        self.positions1 = []
        for line in open('gamefiles/perftsuite.epd'):
            parts = line.split(";")
            depths = [int(s[3:].rstrip()) for s in parts[1:]]
            self.positions1.append( (parts[0], depths) )

        self.positions2 = []
        for line in open('gamefiles/frc_perftsuite.epd'):
            parts = line.split(";")
            depths = [int(s[3:].rstrip()) for s in parts[1:]]
            self.positions2.append( (parts[0], depths) )
    
    def movegen(self, positions):
        for i, (fen, depths) in enumerate(positions):
            board = LBoard(FISCHERRANDOMCHESS)
            fen = fen.split()
            castl = fen[2]
            castl = castl.replace("K", "H")
            castl = castl.replace("Q", "A")
            castl = castl.replace("k", "h")
            castl = castl.replace("q", "a")
            fen[2] = castl
            fen = ' '.join(fen)

            print(i+1, "/", len(positions), "-", fen)
            board.applyFen(fen)
            
            for depth, suposedMoveCount in enumerate(depths):
                if depth+1 > self.MAXDEPTH: break
                self.count = 0
                print("searching depth %d for %d moves" % \
                        (depth+1, suposedMoveCount))
                self.perft (board, depth+1, [])
                self.assertEqual(self.count, suposedMoveCount)

    def testMovegen1(self):
        """Testing FRC variant move generator with perftsuite.epd"""
        print()
        self.MAXDEPTH = 3
        self.movegen(self.positions1)

    def testMovegen2(self):
        """Testing FRC variant move generator with frc_perftsuite.epd"""
        print()
        self.MAXDEPTH = 3
        self.movegen(self.positions2)


if __name__ == '__main__':
    unittest.main()

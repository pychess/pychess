from __future__ import print_function
import unittest

from pychess.Utils.lutils.lmovegen import genAllMoves, genCheckEvasions
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.bitboard import toString, iterBits
from pychess.Utils.lutils.ldata import *
from pychess.Utils.lutils.validator import validateMove

from pychess.Utils.lutils.lmove import toSAN, toAN, parseSAN, ParsingError
from pychess.Utils.const import *


class FindMovesTestCase(unittest.TestCase):
    """Move generator test using perftsuite.epd from
       http://www.albert.nu/programs/sharper/perft.htm"""

    MAXDEPTH = 0
    
    def perft(self, board, depth, prevmoves):
        if depth == 0:
            self.count += 1
            return
        
        if board.isChecked():
            # If we are checked we can use the genCheckEvasions function as well
            # as genAllMoves. Here we try both functions to ensure they return
            # the same result.
            nmoves = []
            for nmove in genAllMoves(board):
                board.applyMove(nmove)
                if board.opIsChecked():
                    board.popMove()
                    continue

                nmoves.append(nmove)
                board.popMove()
                # Validator test
                self.assertTrue(validateMove(board, nmove))
            
            cmoves = []
            
            for move in genCheckEvasions(board):
                board.applyMove(move)
                if board.opIsChecked():
                    board.popMove()
                    continue

                cmoves.append(move)
                board.popMove()
                # Validator test
                self.assertTrue(validateMove(board, move))
            
            # This is not any kind of alphaBeta sort. Only int sorting, to make
            # comparison possible
            nmoves.sort()
            cmoves.sort()
            
            if nmoves == cmoves:
                for move in cmoves:
                    prevmoves.append(toSAN (board, move))
                    board.applyMove(move)
                    self.perft(board, depth-1, prevmoves)
                    board.popMove()
            else:
                print(board)
                print("nmoves")
                for move in nmoves:
                    print(toSAN (board, move))
                print("cmoves")
                for move in cmoves:
                    print(toSAN (board, move))
                self.assertEqual(nmoves, cmoves)
                
        else:
            for move in genAllMoves(board):
                board.applyMove(move)
                if board.opIsChecked():
                    board.popMove()
                    continue
                
                # Validator test
                board.popMove()
                self.assertTrue(validateMove(board, move))
                
                # San test
                san = toSAN (board, move)
                #print(san)
                try:
                    move2 = parseSAN(board, san)
                except ParsingError as e:
                    print(prevmoves)
                    raise ParsingError(e)
                self.assertEqual (move, move2)
                
                board.applyMove (move)
                
                self.perft(board, depth-1, prevmoves)
                board.popMove()
    
    def movegen(self, positions, variant):
        for i, (fen, depths) in enumerate(positions):
            print(i+1, "/", len(positions), "-", fen)
            board = LBoard(variant)
            board.applyFen(fen)
            hash = board.hash
            
            for depth, suposedMoveCount in depths:
                if depth > self.MAXDEPTH:
                    break
                self.count = 0
                print("searching depth %d for %d moves" % \
                        (depth, suposedMoveCount))
                self.perft (board, depth, [])
                self.assertEqual(board.hash, hash)
                self.assertEqual(self.count, suposedMoveCount)

    def testMovegen1(self):
        """Testing NORMAL variant move generator with perftsuite.epd"""
        print()
        #return
        self.MAXDEPTH = 3
        positions = []
        for line in open('gamefiles/perftsuite.epd'):
            if line.startswith("#"):
                continue
            parts = line.split(";")
            depths = [(int(s[1]), int(s[3:].rstrip())) for s in parts[1:]]
            positions.append( (parts[0], depths) )
        
        self.movegen(positions, NORMALCHESS)

    def testMovegen2(self):
        """Testing NORMAL variant move generator with perftsuite2.epd"""
        print()
        print("The movegen test with perftsuite2.epd takes time! If you really want it to run")
        print("put the 'return' line into comment and use pypy instead of python!")
        return
        self.MAXDEPTH = 7
        positions = []
        for line in open('gamefiles/perftsuite2.epd'):
            if line.startswith("#"):
                continue
            parts = line.split(";")
            depths = [(int(s[1]), int(s[3:].rstrip())) for s in parts[1:]]
            positions.append( (parts[0], depths) )
        self.movegen(positions, NORMALCHESS)

    def testMovegen3(self):
        """Testing SITTUYINCHESS variant move generator"""
        positions = [("8/6k1/6p1/3s2P1/3npR2/2r5/p2N2F1/3K4 b - - 0 49", [(1, 32),(2, 653),(3, 18439),(4, 357804)])]
        print()
        #return
        self.MAXDEPTH = 3
        self.movegen(positions, SITTUYINCHESS)

    def testMovegen4(self):
        """Testing CAMBODIANCHESS variant move generator"""
        positions = [("rnsmksnr/8/ppp1pppp/3p4/4P3/PPPP1PPP/8/RNSKMSNR w - - 0 2", [(1, 27), (2, 728)]),
                     ("rns2snr/2m1k3/ppp1pppp/3p4/4P3/PPPP1PPP/3K1M2/RNS2SNR w - - 4 4", [(1, 23), (2, 527), (3, 12264)]),
                    ]
        print()
        #return
        self.MAXDEPTH = 3
        self.movegen(positions, CAMBODIANCHESS)

    def testMovegen5(self):
        """Testing MAKRUK variant move generator"""
        positions = [("rnsmksnr/8/ppppp1pp/2P5/5p2/PP1PPPPP/8/RNSKMSNR w - - 0 3", [(1, 26), (2, 665), (3, 17062), (4, 432413)])]
        print()
        #return
        self.MAXDEPTH = 3
        self.movegen(positions, MAKRUKCHESS)

if __name__ == '__main__':
    unittest.main()

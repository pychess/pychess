import unittest

from pychess.Utils.lutils.lmovegen import genAllMoves, genCheckEvasions
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.bitboard import toString, iterBits
from pychess.Utils.lutils.ldata import *
from pychess.Utils.lutils.validator import validateMove

from pychess.Utils.lutils.lmove import toSAN, toAN, parseSAN, ParsingError
from pychess.Utils.const import *

MAXDEPTH = 3

try:
    import psyco
    psyco.bind(genAllMoves)
except ImportError:
    print 'psyco not found'

class FindMovesTestCase(unittest.TestCase):
    """Move generator test using perftsuite.epd from
       http://www.albert.nu/programs/sharper/perft.htm"""
    
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
                print board
                print "nmoves"
                for move in nmoves:
                    print toSAN (board, move)
                print "cmoves"
                for move in cmoves:
                    print toSAN (board, move)
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
                try:
                    move2 = parseSAN(board, san)
                except ParsingError, e:
                    print prevmoves
                    raise ParsingError, e
                self.assertEqual (move, move2)
                
                board.applyMove (move)
                
                self.perft(board, depth-1, prevmoves)
                board.popMove()
    
    def setUp(self):
        self.positions = []
        for line in open('gamefiles/perftsuite.epd'):
            parts = line.split(";")
            depths = [int(s[3:].rstrip()) for s in parts[1:]]
            self.positions.append( (parts[0], depths) )
    
    def movegen(self, board, positions):
        for i, (fen, depths) in enumerate(positions):
            if board.variant == FISCHERRANDOMCHESS:
                fen = fen.split()
                castl = fen[2]
                castl = castl.replace("K", "H")
                castl = castl.replace("Q", "A")
                castl = castl.replace("k", "h")
                castl = castl.replace("q", "a")
                fen[2] = castl
                fen = ' '.join(fen)

            print i+1, "/", len(positions), "-", fen
            board.applyFen(fen)
            hash = board.hash
            
            for depth, suposedMoveCount in enumerate(depths):
                if depth+1 > MAXDEPTH: break
                self.count = 0
                print "searching depth %d for %d moves" % \
                        (depth+1, suposedMoveCount)
                self.perft (board, depth+1, [])
                self.assertEqual(board.hash, hash)
                self.assertEqual(self.count, suposedMoveCount)

    def testMovegen1(self):
        """Testing NORMAL variant move generator with perftsuite.epd"""
        print
        self.movegen(LBoard(NORMALCHESS), self.positions)


#class FRCFindMovesTestCase(FindMovesTestCase):
    #def setUp(self):
        #self.positions1 = []
        #for line in open('gamefiles/perftsuite.epd'):
            #parts = line.split(";")
            #depths = [int(s[3:].rstrip()) for s in parts[1:]]
            #self.positions1.append( (parts[0], depths) )

        #self.positions2 = []
        #for line in open('gamefiles/frc_perftsuite.epd'):
            #parts = line.split(";")
            #depths = [int(s[3:].rstrip()) for s in parts[1:]]
            #self.positions2.append( (parts[0], depths) )

    #def testMovegen1(self):
    #    """Testing FRC variant move generator with perftsuite.epd"""
    #    print
    #    self.movegen(LBoard(FISCHERRANDOMCHESS), self.positions1)

    #def testMovegen2(self):
    #    """Testing FRC variant move generator with frc_perftsuite.epd"""
    #    print
    #    self.movegen(LBoard(FISCHERRANDOMCHESS), self.positions2)


if __name__ == '__main__':
    unittest.main()

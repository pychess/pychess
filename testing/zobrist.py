import unittest

from pychess.Utils.const import *
from pychess.Utils.Board import Board
from pychess.Utils.lutils.leval import LBoard
from pychess.Utils.lutils.lmove import parseAN

FEN = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"

class ZobristTestCase(unittest.TestCase):

    def make_move(self, an_move):
        self.board.applyMove(parseAN(self.board, an_move))
    
    def setUp(self):
        self.board = LBoard(Board)
        self.board.applyFen(FEN)
         
    def testZobrist_1(self):
        """Testing zobrist hashing with simple move and take back"""
        
        hash = self.board.hash
        self.make_move("c3b5")
        self.board.color = 1 - self.board.color
        self.make_move("b5c3")

        self.assertEqual(hash, self.board.hash)

    def testZobrist_2(self):
        """Testing zobrist hashing with W00,B00,a1b1 vs. a1b1,B00,W00"""
        
        self.make_move("e1g1")
        self.make_move("e8g8")
        self.make_move("a1b1")
        hash1 = self.board.hash
        
        self.board.popMove()
        self.board.popMove()
        self.board.popMove()

        self.make_move("a1b1")
        self.make_move("e8g8")
        self.make_move("e1g1")
        hash2 = self.board.hash
        
        self.assertEqual(hash1, hash2)

    def testZobrist_3(self):
        """Testing zobrist hashing with W000,B000,h1g1 vs. h1g1,B000,W000"""
        
        self.make_move("e1c1")
        self.make_move("e8c8")
        self.make_move("h1g1")
        hash1 = self.board.hash
        
        self.board.popMove()
        self.board.popMove()
        self.board.popMove()

        self.make_move("h1g1")
        self.make_move("e8c8")
        self.make_move("e1c1")
        hash2 = self.board.hash

        self.assertEqual(hash1, hash2)

    def testZobrist_4(self):
        """Testing zobrist hashing with en-passant"""
        
        self.make_move("a2a4")
        self.make_move("b4a3")
        self.make_move("e1c1")
        self.make_move("c7c5")
        self.make_move("d5c6")
        self.make_move("e8c8")
        hash1 = self.board.hash
        
        self.board.popMove()
        self.board.popMove()
        self.board.popMove()
        self.board.popMove()
        self.board.popMove()
        self.board.popMove()

        self.make_move("e1c1")
        self.make_move("c7c5")
        self.make_move("d5c6")
        self.make_move("e8c8")
        self.make_move("a2a4")
        self.make_move("b4a3")
        hash2 = self.board.hash

        self.assertEqual(hash1, hash2)

if __name__ == '__main__':
    unittest.main()

import unittest

from pychess.Utils.Cord import Cord
from pychess.Utils.Move import Move
from pychess.Utils.History import startBoard


class HashTestCase(unittest.TestCase):

    def setUp(self):
        self.board = startBoard()

    def testSanity(self):
        """Sanity testing for zobrist hash keys"""
        hash0 = self.board.myhash

        board1 = self.board.move(Move(Cord('e2'), Cord('e4')))
        hash1 = board1.myhash
        self.assert_(hash0 != hash1)

        board2 = board1.move(Move(Cord('e4'), Cord('e2')))
        hash2 = board2.myhash
        self.assertEqual(hash0, hash2)

if __name__ == '__main__':
    unittest.main()

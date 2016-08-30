import unittest

from pychess.Savers import pgn
from pychess.Utils.lutils import ldraw
from pychess.System.protoopen import protoopen


class DrawTestCase(unittest.TestCase):
    def setUp(self):
        self.f1 = protoopen('gamefiles/3fold.pgn')
        self.PgnFile1 = pgn.load(self.f1)

        self.f2 = protoopen('gamefiles/bilbao.pgn')
        self.PgnFile2 = pgn.load(self.f2)

        self.f3 = protoopen('gamefiles/material.pgn')
        self.PgnFile3 = pgn.load(self.f3)

    def tearDown(self):
        self.f1.close()
        self.f2.close()
        self.f3.close()

    def test1(self):
        """Testing the same position, for the third time"""
        for i, game in enumerate(self.PgnFile1.games):
            model = self.PgnFile1.loadToModel(i)

            lboard = model.boards[-2].board
            self.assertTrue(lboard.repetitionCount() < 3)

            lboard = model.boards[-1].board
            self.assertEqual(lboard.repetitionCount(), 3)

    def test2(self):
        """Testing the 50 move rule"""
        for i, game in enumerate(self.PgnFile2.games):
            model = self.PgnFile2.loadToModel(i)

            lboard = model.boards[-2].board
            self.assertEqual(ldraw.testFifty(lboard), False)

            lboard = model.boards[-1].board
            self.assertEqual(ldraw.testFifty(lboard), True)

    def test3(self):
        """Testing too few material"""
        for i, game in enumerate(self.PgnFile3.games):
            model = self.PgnFile3.loadToModel(i)

            lboard = model.boards[-2].board
            self.assertEqual(ldraw.testMaterial(lboard), False)

            lboard = model.boards[-1].board
            self.assertEqual(ldraw.testMaterial(lboard), True)


if __name__ == '__main__':
    unittest.main()

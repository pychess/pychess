import unittest

from pychess.Savers import pgn
from pychess.Utils.lutils import ldraw


class DrawTestCase(unittest.TestCase):
    
    def setUp(self):
        with open('gamefiles/3fold.pgn') as f1:
            self.PgnFile1 = pgn.load(f1)

        with open('gamefiles/bilbao.pgn') as f2:
            self.PgnFile2 = pgn.load(f2)

        with open('gamefiles/material.pgn') as f3:
            self.PgnFile3 = pgn.load(f3)

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

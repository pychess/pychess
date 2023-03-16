import unittest

from pychess.Savers import pgn
from pychess.Utils.lutils import ldraw
from pychess.System.protoopen import protoopen


class DrawTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f1 = protoopen("gamefiles/3fold.pgn")
        cls.PgnFile1 = pgn.load(cls.f1)
        cls.PgnFile1.get_records()

        cls.f2 = protoopen("gamefiles/bilbao.pgn")
        cls.PgnFile2 = pgn.load(cls.f2)
        cls.PgnFile2.get_records()

        cls.f3 = protoopen("gamefiles/material.pgn")
        cls.PgnFile3 = pgn.load(cls.f3)
        cls.PgnFile3.get_records()

    @classmethod
    def tearDownClass(cls):
        cls.f1.close()
        cls.f2.close()
        cls.f3.close()

    def test1(self):
        """Testing the same position, for the third time"""
        for game in self.PgnFile1.games:
            model = self.PgnFile1.loadToModel(game)

            lboard = model.boards[-2].board
            self.assertTrue(lboard.repetitionCount() < 3)

            lboard = model.boards[-1].board
            self.assertEqual(lboard.repetitionCount(), 3)

    def test2(self):
        """Testing the 50 move rule"""
        for game in self.PgnFile2.games:
            model = self.PgnFile2.loadToModel(game)

            lboard = model.boards[-2].board
            self.assertEqual(ldraw.testFifty(lboard), False)

            lboard = model.boards[-1].board
            self.assertEqual(ldraw.testFifty(lboard), True)

    def test3(self):
        """Testing too few material"""
        for game in self.PgnFile3.games:
            model = self.PgnFile3.loadToModel(game)

            lboard = model.boards[-2].board
            self.assertEqual(ldraw.testMaterial(lboard), False)

            lboard = model.boards[-1].board
            self.assertEqual(ldraw.testMaterial(lboard), True)


if __name__ == "__main__":
    unittest.main()

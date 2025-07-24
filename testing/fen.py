import os.path
import unittest

from pychess.Utils.lutils.LBoard import LBoard


class FenTestCase(unittest.TestCase):
    def testFEN(self):
        """Testing board-FEN conversion with several positions"""

        positions = []
        curdir = os.path.dirname(__file__)
        with open("%s/gamefiles/perftsuite.epd" % curdir) as f:
            for line in f:
                semi = line.find(" ;")
                positions.append(line[:semi])

        for i, fenstr in enumerate(positions[1:]):
            board = LBoard()
            board.applyFen(fenstr)
            fenstr2 = board.asFen()
            self.assertEqual(fenstr, fenstr2)


if __name__ == "__main__":
    unittest.main()

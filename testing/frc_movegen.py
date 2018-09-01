import unittest

from pychess import MSYS2
from pychess.Utils.lutils.lmovegen import genAllMoves
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.validator import validateMove

from pychess.Utils.const import FISCHERRANDOMCHESS


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

            board.applyMove(move)
            self.perft(board, depth - 1, prevmoves)
            board.popMove()

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

            print(i + 1, "/", len(positions), "-", fen)
            board.applyFen(fen)

            for depth, suposedMoveCount in enumerate(depths):
                if depth + 1 > self.MAXDEPTH:
                    break
                self.count = 0
                print("searching depth %d for %d moves" % (depth + 1, suposedMoveCount))
                self.perft(board, depth + 1, [])
                self.assertEqual(self.count, suposedMoveCount)

    @unittest.skipIf(MSYS2, "Testing perft takes time. Leave it to travis.")
    def testMovegen1(self):
        """Testing FRC variant move generator with perftsuite.epd"""
        print()
        self.MAXDEPTH = 3
        positions = []
        with open('gamefiles/perftsuite.epd') as f:
            for line in f:
                parts = line.split(";")
                depths = [int(s[3:].rstrip()) for s in parts[1:]]
                positions.append((parts[0], depths))
        self.movegen(positions)

    @unittest.skipIf(MSYS2, "Testing perft takes time. Leave it to travis.")
    def testMovegen2(self):
        """Testing FRC variant move generator with frc_perftsuite.epd"""
        print()
        self.MAXDEPTH = 3
        positions = []
        with open('gamefiles/frc_perftsuite.epd') as f:
            for line in f:
                parts = line.split(";")
                depths = [int(s[3:].rstrip()) for s in parts[1:]]
                positions.append((parts[0], depths))
        self.movegen(positions)


if __name__ == '__main__':
    unittest.main()

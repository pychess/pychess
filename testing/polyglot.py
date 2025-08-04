import asyncio
import os
import unittest

from pychess.System import uistuff
from pychess.widgets import gamewidget
from pychess.perspectives.games import Games
from pychess.perspectives.database import Database
from pychess.perspectives import perspective_manager
from pychess.Utils.const import A2, A4, E2, E4
from pychess.Utils import book
from pychess.Utils.Board import Board
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmovegen import newMove

# Examples taken from http://alpha.uhasselt.be/Research/Algebra/Toga/book_format.html
testcases = [
    [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        0x463B96181691FC9C,
        "",
    ],
    [
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        0x823C9B50FD114196,
        "e2e4",
    ],
    [
        "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2",
        0x0756B94461C50FB0,
        "e2e4 d7d5",
    ],
    [
        "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2",
        0x662FAFB965DB29D4,
        "e2e4 d7d5 e4e5",
    ],
    [
        "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3",
        0x22A48B5A8E47FF78,
        "e2e4 d7d5 e4e5 f7f5",
    ],
    [
        "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPPKPPP/RNBQ1BNR b kq - 0 3",
        0x652A607CA3F242C1,
        "e2e4 d7d5 e4e5 f7f5 e1e2",
    ],
    [
        "rnbq1bnr/ppp1pkpp/8/3pPp2/8/8/PPPPKPPP/RNBQ1BNR w - - 0 4",
        0x00FDD303C946BDD9,
        "e2e4 d7d5 e4e5 f7f5 e1e2 e8f7",
    ],
    [
        "rnbqkbnr/p1pppppp/8/8/PpP4P/8/1P1PPPP1/RNBQKBNR b KQkq c3 0 3",
        0x3C8123EA7B067637,
        "a2a4 b7b5 h2h4 b5b4 c2c4",
    ],
    [
        "rnbqkbnr/p1pppppp/8/8/P6P/R1p5/1P1PPPP1/1NBQKBNR b Kkq - 0 4",
        0x5C3F9B829B279560,
        "a2a4 b7b5 h2h4 b5b4 c2c4 b4c3 a1a3",
    ],
]


pgn = """
[Event ""]
[Result "1-0"]

1. e4 d5 2. e5 f5 3. Ke2 Kf7 1-0

[Event ""]
[Result "0-1"]

1. a4 b5 2. h4 b4 3. c4 bxc3 Ra3 0-1
"""
PGN = "polyglot.pgn"
BIN = "polyglot_book.bin"
SCOUT = "polyglot.scout"
SQLITE = "polyglot.sqlite"


class PolyglotTestCase(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        for fi in (PGN, BIN, SCOUT, SQLITE):
            if os.path.isfile(fi):
                os.remove(fi)

        with open(PGN, "w") as f:
            f.write(pgn)

        cls.saved_book_path = book.path
        book.path = BIN
        book.bookfile = True

    @classmethod
    def tearDownClass(cls):
        book.path = cls.saved_book_path

        for fi in (PGN, BIN, SCOUT, SQLITE):
            if os.path.isfile(fi):
                try:
                    os.remove(fi)
                except PermissionError:
                    print("Can't remove %s because someone is using it" % fi)

    def testPolyglot_1(self):
        """Testing hash keys agree with Polyglot's"""

        for testcase in testcases:
            board = LBoard(Board)
            board.applyFen(testcase[0])
            self.assertEqual(board.hash, testcase[1])

    async def testPolyglot_2(self):
        """Testing Polyglot book creation"""

        widgets = uistuff.GladeWidgets("PyChess.glade")
        gamewidget.setWidgets(widgets)
        perspective_manager.set_widgets(widgets)

        self.games_persp = Games()
        perspective_manager.add_perspective(self.games_persp)

        self.database_persp = Database()
        self.database_persp.create_toolbuttons()
        perspective_manager.add_perspective(self.database_persp)

        self.database_persp.open_chessfile(PGN)

        def on_book_created(persp, event):
            self.assertTrue(os.path.isfile(BIN))

            testcase = testcases[0]
            board = LBoard(Board)
            board.applyFen(testcase[0])
            openings = book.getOpenings(board)
            self.assertEqual(
                sorted(openings),
                sorted([(newMove(E2, E4), 2, 0), (newMove(A2, A4), 0, 0)]),
            )

            testcase = testcases[-1]
            board = LBoard(Board)
            board.applyFen(testcase[0])
            openings = book.getOpenings(board)
            self.assertEqual(openings, [])

            event.set()

        event = asyncio.Event()
        self.database_persp.connect("bookfile_created", on_book_created, event)

        self.database_persp.create_book(BIN)

        await event.wait()


if __name__ == "__main__":
    unittest.main()

import unittest
import logging

from pychess.ic.FICSObjects import FICSPlayer, FICSGame
from pychess.ic import (
    BLOCK_START,
    BLOCK_SEPARATOR,
    BLOCK_END,
    BLOCK_POSE_START,
    BLOCK_POSE_END,
    IC_POS_OBSERVING_EXAMINATION,
    IC_POS_EXAMINATING,
)
from pychess.System import uistuff
from pychess.widgets import gamewidget
from pychess.perspectives import perspective_manager
from pychess.perspectives.fics import FICS
from pychess.perspectives.games import Games
from ficsmanagers import EmittingTestCase
from pychess.System.Log import log

log.logger.setLevel(logging.DEBUG)


class ExamineGameTests(EmittingTestCase):
    def setUp(self):
        EmittingTestCase.setUp(self)
        self.loop.set_debug(enabled=True)

        self.manager = self.connection.bm

        widgets = uistuff.GladeWidgets("PyChess.glade")
        gamewidget.setWidgets(widgets)
        perspective_manager.set_widgets(widgets)

        self.games_persp = Games()
        perspective_manager.add_perspective(self.games_persp)

        self.fics_persp = FICS()
        perspective_manager.add_perspective(self.fics_persp)

        self.fics_persp.connection = self.connection
        self.connection.bm.connect(
            "obsGameCreated", self.fics_persp.onObserveGameCreated
        )
        self.connection.bm.connect(
            "exGameCreated", self.fics_persp.onObserveGameCreated
        )

    def test1(self):
        """Test puzzlebot starting a new mate in 2 puzzle"""

        # tell puzzlebot gm2
        lines = [
            BLOCK_START + "92" + BLOCK_SEPARATOR + "132" + BLOCK_SEPARATOR,
            "(told puzzlebot, who is examining a game)",
            BLOCK_END,
            "fics% ",
            BLOCK_POSE_START
            + "\n"
            + BLOCK_START
            + "0"
            + BLOCK_SEPARATOR
            + "80"
            + BLOCK_SEPARATOR,
            "You are now observing game 127.",
            "Game 127: gbtami (0) puzzlebot (0) unrated untimed 0 0",
            "",
            "<12> --kr---r pp--bppp ----bn-- -Npp---q -----B-Q ---B---- PPP--PPP -K-R---R W -1 0 0 0 0 0 127 gbtami puzzlebot -2 0 0 0 0 0 0 1 none (0:00.000) none 0 0 0",
            BLOCK_END,
            "fics% ",
            BLOCK_POSE_END,
        ]

        signal = "obsGameCreated"

        game = FICSGame(
            FICSPlayer("gbtami"),
            FICSPlayer("puzzlebot"),
            gameno=127,
            relation=IC_POS_OBSERVING_EXAMINATION,
        )
        game = self.connection.games.get(game)
        expectedResults = (game,)
        self.runAndAssertEquals(signal, lines, expectedResults)

        print(self.games_persp.cur_gmwidg().gamemodel)

        lines = [
            "Removing game 127 from observation list." "",
            "puzzlebot has made you an examiner of game 127.",
            "",
            "<12> --kr---r pp--bppp ----bn-- -Npp---q -----B-Q ---B---- PPP--PPP -K-R---R W -1 0 0 0 0 0 127 gbtami puzzlebot 2 0 0 0 0 0 0 1 none (0:00.000) none 0 0 0",
            "fics% ",
            "puzzlebot(TD)(----)[127] kibitzes: This is mate problem number [00655]",
            "fics% ",
            "puzzlebot(TD)(----)[127] kibitzes: White moves and mates in 2 moves.",
            "fics% ",
        ]

        async def coro():
            await self.connection.process_lines(lines)

        self.loop.run_until_complete(coro())

        # check that our relation has changed as expected
        self.assertEqual(game.relation, IC_POS_EXAMINATING)

        # try with a wrong move first: h4h5
        lines = [
            "puzzlebot stopped examining game 127.",
            "fics% ",
            BLOCK_START + "109" + BLOCK_SEPARATOR + "1" + BLOCK_SEPARATOR,
            "<12> --kr---r pp--bppp ----bn-- -Npp---Q -----B-- ---B---- PPP--PPP -K-R---R B -1 0 0 0 0 0 127 gbtami puzzlebot 2 0 0 0 247 0 0 1 Q/h4-h5 (0:00.000) Qxh5 0 0 0",
            "",
            "Game 127: gbtami moves: Qxh5",
            BLOCK_END,
            "fics% ",
        ]

        async def coro():
            await self.connection.process_lines(lines)

        self.loop.run_until_complete(coro())

        game = self.connection.games.get(game)
        self.assertEqual(game.move_queue.qsize(), 0)

        print(self.games_persp.cur_gmwidg().gamemodel.boards[-1])

        self.assertEqual(self.games_persp.cur_gmwidg().gamemodel.ply, 1)

        # puzzlebot just backs up our move and sends the puzzle starting position again
        lines = [
            BLOCK_POSE_START
            + "\n"
            + BLOCK_START
            + "0"
            + BLOCK_SEPARATOR
            + "80"
            + BLOCK_SEPARATOR,
            "puzzlebot is now an examiner of game 127.",
            BLOCK_END,
            "fics% ",
            BLOCK_POSE_END,
            "Game 127: puzzlebot backs up 1 move.",
            "",
            "<12> --kr---r pp--bppp ----bn-- -Npp---q -----B-Q ---B---- PPP--PPP -K-R---R W -1 0 0 0 0 0 127 gbtami puzzlebot 2 0 0 34 35 0 0 1 none (0:00.000) none 0 0 0",
            "fics% ",
            "Game 127: Still in progress *",
            "",
            "puzzlebot(TD)(----)[127] kibitzes: There is a better move.",
            "fics% ",
        ]

        async def coro():
            await self.connection.process_lines(lines)

        self.loop.run_until_complete(coro())

        self.assertEqual(game.move_queue.qsize(), 0)

        print(self.games_persp.cur_gmwidg().gamemodel.boards[-1])

        self.assertEqual(self.games_persp.cur_gmwidg().gamemodel.ply, 0)

        # now we take the good move: b5a7
        lines = [
            "puzzlebot stopped examining game 127.",
            "fics% ",
            BLOCK_START + "114" + BLOCK_SEPARATOR + "1" + BLOCK_SEPARATOR,
            "<12> --kr---r Np--bppp ----bn-- --pp---q -----B-Q ---B---- PPP--PPP -K-R---R B -1 0 0 0 0 0 127 gbtami puzzlebot 2 0 0 34 34 0 0 1 N/b5-a7 (0:00.000) Nxa7+ 0 0 0",
            "",
            "Game 127: gbtami moves: Nxa7+",
            BLOCK_END,
            "fics% ",
        ]

        async def coro():
            await self.connection.process_lines(lines)

        self.loop.run_until_complete(coro())

        self.assertEqual(game.move_queue.qsize(), 0)

        print(self.games_persp.cur_gmwidg().gamemodel.boards[-1])

        self.assertEqual(self.games_persp.cur_gmwidg().gamemodel.ply, 1)

        # puzzlebot moves
        lines = [
            BLOCK_POSE_START
            + "\n"
            + BLOCK_START
            + "0"
            + BLOCK_SEPARATOR
            + "75"
            + BLOCK_SEPARATOR,
            "puzzlebot is now an examiner of game 127.",
            BLOCK_END,
            "fics% ",
            BLOCK_POSE_END,
            "<12> ---r---r Np-kbppp ----bn-- --pp---q -----B-Q ---B---- PPP--PPP -K-R---R W -1 0 0 0 0 1 127 gbtami puzzlebot 2 0 0 34 34 0 0 2 K/c8-d7 (0:00.000) Kd7 0 0 0",
            "fics% ",
            "Game 127: puzzlebot moves: Kd7",
            "fics% ",
        ]

        async def coro():
            await self.connection.process_lines(lines)

        self.loop.run_until_complete(coro())

        self.assertEqual(game.move_queue.qsize(), 0)

        print(self.games_persp.cur_gmwidg().gamemodel.boards[-1])
        print(self.games_persp.cur_gmwidg().gamemodel.moves)

        self.assertEqual(self.games_persp.cur_gmwidg().gamemodel.ply, 2)

        # we make the mating move: d3b5
        lines = [
            "puzzlebot stopped examining game 127.",
            "fics% ",
            BLOCK_START + "117" + BLOCK_SEPARATOR + "1" + BLOCK_SEPARATOR,
            "<12> ---r---r Np-kbppp ----bn-- -Bpp---q -----B-Q -------- PPP--PPP -K-R---R B -1 0 0 0 0 2 127 gbtami puzzlebot 2 0 0 34 34 0 0 2 B/d3-b5 (0:00.000) Bb5# 0 0 0",
            "" "Game 127: gbtami moves: Bb5#",
            "",
            "Game 127: Black checkmated 1-0",
            BLOCK_END,
            "fics% ",
            "puzzlebot(TD)(----)[127] kibitzes: You solved problem number [00655] in 02m01s",
            "fics% ",
            "puzzlebot(TD)(----)[127] kibitzes: You made 1 wrong moves and needed 0 hints",
            "fics% ",
            'puzzlebot(TD)(----)[127] kibitzes: To solve the next problem type "tell puzzlebot next". To solve the previous problem type "tell puzzlebot previous" To automatically load problems type "tell puzzlebot auto" Or type "tell puzzlebot getmate" or "tell puzzlebot gettactics" or "tell puzzlebot getstudy"',
            "fics% ",
        ]

        async def coro():
            await self.connection.process_lines(lines)

        self.loop.run_until_complete(coro())

        self.assertEqual(game.move_queue.qsize(), 0)

        print(self.games_persp.cur_gmwidg().gamemodel.boards[-1])

        self.assertEqual(self.games_persp.cur_gmwidg().gamemodel.ply, 3)

        ########################################################################
        # now start another mate in 2 puzzle
        # tell puzzlebot next
        lines = [
            BLOCK_START + "125" + BLOCK_SEPARATOR + "132" + BLOCK_SEPARATOR,
            "(told puzzlebot, who is examining a game)",
            BLOCK_END,
            "fics% ",
            BLOCK_POSE_START
            + "\n"
            + BLOCK_START
            + "0"
            + BLOCK_SEPARATOR
            + "80"
            + BLOCK_SEPARATOR,
            "You are now observing game 127.",
            "Game 127: gbtami (0) puzzlebot (0) unrated untimed 0 0",
            "",
            "<12> -----k-- -R------ --p--n-- -------- P-P--pr- -P---RNK -----PP- ----r--- B -1 0 0 0 0 0 127 puzzlebot gbtami -2 0 0 0 0 0 0 1 none (0:00.000) none 0 0 0",
        ]

        signal = "obsGameCreated"

        game = FICSGame(
            FICSPlayer("puzzlebot"),
            FICSPlayer("gbtami"),
            gameno=127,
            relation=IC_POS_OBSERVING_EXAMINATION,
        )
        game = self.connection.games.get(game)
        expectedResults = (game,)
        self.runAndAssertEquals(signal, lines, expectedResults)

        print(self.games_persp.cur_gmwidg().gamemodel)

        lines = [
            "Removing game 127 from observation list." "",
            "puzzlebot has made you an examiner of game 127.",
            "",
            "<12> -----k-- -R------ --p--n-- -------- P-P--pr- -P---RNK -----PP- ----r--- B -1 0 0 0 0 0 127 puzzlebot gbtami 2 0 0 0 0 0 0 1 none (0:00.000) none 0 0 0",
            "fics% ",
            "puzzlebot(TD)(----)[127] kibitzes: This is mate problem number [00656]",
            "fics% ",
            "puzzlebot(TD)(----)[127] kibitzes: Black moves and mates in 2 moves.",
            "fics% ",
        ]

        async def coro():
            await self.connection.process_lines(lines)

        self.loop.run_until_complete(coro())

        # check that our relation has changed as expected
        self.assertEqual(game.relation, IC_POS_EXAMINATING)

        # g4g3
        lines = [
            "puzzlebot stopped examining game 127.",
            "fics% ",
            BLOCK_START + "147" + BLOCK_SEPARATOR + "1" + BLOCK_SEPARATOR,
            "<12> -----k-- -R------ --p--n-- -------- P-P--p-- -P---RrK -----PP- ----r--- W -1 0 0 0 0 0 127 puzzlebot gbtami 2 0 0 253 0 0 0 2 R/g4-g3 (0:00.000) Rxg3+ 0 0 0",
            "",
            "Game 127: gbtami moves: Rxg3+",
            BLOCK_END,
            "fics% ",
        ]

        async def coro():
            await self.connection.process_lines(lines)

        self.loop.run_until_complete(coro())

        self.assertEqual(game.move_queue.qsize(), 0)

        print(self.games_persp.cur_gmwidg().gamemodel.boards[-1])

        self.assertEqual(self.games_persp.cur_gmwidg().gamemodel.ply, 2)

        # puzzlebot moves
        lines = [
            BLOCK_POSE_START
            + "\n"
            + BLOCK_START
            + "0"
            + BLOCK_SEPARATOR
            + "75"
            + BLOCK_SEPARATOR,
            "puzzlebot is now an examiner of game 127.",
            BLOCK_END,
            "fics% ",
            BLOCK_POSE_END,
            "fics% ",
            "<12> -----k-- -R------ --p--n-- -------- P-P--p-- -P---RPK ------P- ----r--- B -1 0 0 0 0 0 127 puzzlebot gbtami 2 0 0 253 251 0 0 2 P/f2-g3 (0:00.000) fxg3 0 0 0",
            "Game 127: puzzlebot moves: fxg3",
            "fics% ",
        ]

        async def coro():
            await self.connection.process_lines(lines)

        self.loop.run_until_complete(coro())

        self.assertEqual(game.move_queue.qsize(), 0)

        print(self.games_persp.cur_gmwidg().gamemodel.boards[-1])

        self.assertEqual(self.games_persp.cur_gmwidg().gamemodel.ply, 3)

        # we make the mating move: e1h1
        lines = [
            "puzzlebot stopped examining game 127.",
            "fics% ",
            BLOCK_START + "150" + BLOCK_SEPARATOR + "1" + BLOCK_SEPARATOR,
            "<12> -----k-- -R------ --p--n-- -------- P-P--p-- -P---RPK ------P- -------r W -1 0 0 0 0 1 127 puzzlebot gbtami 2 0 0 253 251 0 0 3 R/e1-h1 (0:00.000) Rh1# 0 0 0",
            "" "Game 127: gbtami moves: Rh1#",
            "",
            "Game 127: White checkmated 0-1",
            BLOCK_END,
            "fics% ",
            "puzzlebot(TD)(----)[127] kibitzes: You solved problem number [00656] in 00m45s",
            "fics% ",
            "puzzlebot(TD)(----)[127] kibitzes: You made 1 wrong moves and needed 0 hints",
            "fics% ",
            'puzzlebot(TD)(----)[127] kibitzes: To solve the next problem type "tell puzzlebot next". To solve the previous problem type "tell puzzlebot previous" To automatically load problems type "tell puzzlebot auto" Or type "tell puzzlebot getmate" or "tell puzzlebot gettactics" or "tell puzzlebot getstudy"',
            "fics% ",
        ]

        async def coro():
            await self.connection.process_lines(lines)

        self.loop.run_until_complete(coro())

        self.assertEqual(game.move_queue.qsize(), 0)

        print(self.games_persp.cur_gmwidg().gamemodel.boards[-1])

        self.assertEqual(self.games_persp.cur_gmwidg().gamemodel.ply, 4)


if __name__ == "__main__":
    unittest.main()

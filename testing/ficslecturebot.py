import unittest
import logging

from pychess.ic.FICSObjects import FICSPlayer, FICSGame
from pychess.ic import BLOCK_START, BLOCK_SEPARATOR, BLOCK_END
from pychess.System import uistuff
from pychess.widgets import gamewidget
from pychess.perspectives import perspective_manager
from pychess.perspectives.fics import FICS
from pychess.perspectives.games import Games
from ficsmanagers import EmittingTestCase
from pychess.System.Log import log
log.logger.setLevel(logging.DEBUG)


class ObserveGameTests(EmittingTestCase):
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
        self.connection.bm.connect("obsGameCreated", self.fics_persp.onObserveGameCreated)
        self.connection.bm.connect("exGameCreated", self.fics_persp.onObserveGameCreated)

    def test1(self):
        """ Test following lecturebot starting new lecture after finishing previous one """

        lines = [
            'LectureBot(TD)(----)[1] kibitzes: That concludes this lecture. If this lecture inspired you to write your own lecture, "finger LectureBot" and read note 8. toddmf would really like to hear from you about LectureBot. Please send him comments! Hope to see you all again soon!',
            'fics% ',
            'LectureBot stopped examining game 1.',
            '',
            'Game 1 (which you were observing) has no examiners.',
            'Removing game 1 from observation list.',
            'fics% ',
            'LectureBot, whom you are following, has started examining a game.',
            'You are now observing game 1.',
            'Game 1: LectureBot (0) LectureBot (0) unrated untimed 0 0',
            '',
            '<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 1 LectureBot LectureBot -2 0 0 39 39 0 0 1 none (0:00.000) none 0 0 0',
        ]

        signal = 'obsGameCreated'

        game = FICSGame(
            FICSPlayer("LectureBot"),
            FICSPlayer("LectureBot"),
            gameno=1)
        game = self.connection.games.get(game)
        expectedResults = (game, )
        self.runAndAssertEquals(signal, lines, expectedResults)

        print(self.games_persp.cur_gmwidg().gamemodel)

        lines = [
            '<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 1 Henley LectureBot -2 0 0 39 39 0 0 1 none (0:00.000) none 0 0 0',
            '<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 1 Henley Browne -2 0 0 39 39 0 0 1 none (0:00.000) none 0 0 0',
            '<12> rnbqkbnr pppppppp -------- -------- -------- -----N-- PPPPPPPP RNBQKB-R B -1 1 1 1 1 1 1 Henley Browne -2 0 0 39 39 0 0 1 N/g1-f3 (0:00.000) Nf3 0 0 0',
            'fics% ',
            'Game 1: LectureBot moves: Nf3',
        ]

        def coro():
            yield from self.connection.process_lines(lines)
        self.loop.run_until_complete(coro())

        self.assertEqual(game.move_queue.qsize(), 0)

        print(self.games_persp.cur_gmwidg().gamemodel)

        self.assertEqual(self.games_persp.cur_gmwidg().gamemodel.ply, 1)

        lines = [
            '<12> rnbqkbnr pp-ppppp -------- --p----- -------- -----N-- PPPPPPPP RNBQKB-R W 2 1 1 1 1 0 1 Henley Browne -2 0 0 39 39 0 0 2 P/c7-c5 (0:00.000) c5 0 0 0',
            'fics% ',
            'Game 1: LectureBot moves: c5',
            '<12> rnbqkbnr pp-ppppp -------- --p----- -------- -----NP- PPPPPP-P RNBQKB-R B -1 1 1 1 1 0 1 Henley Browne -2 0 0 39 39 0 0 2 P/g2-g3 (0:00.000) g3 0 0 0',
            'fics% '
            'Game 1: LectureBot moves: g3',
            '<12> rnbqkbnr p--ppppp -p------ --p----- -------- -----NP- PPPPPP-P RNBQKB-R W -1 1 1 1 1 0 1 Henley Browne -2 0 0 39 39 0 0 3 P/b7-b6 (0:00.000) b6 0 0 0',
            'fics% '
            'Game 1: LectureBot moves: b6',
        ]

        def coro():
            yield from self.connection.process_lines(lines)
        self.loop.run_until_complete(coro())

        self.assertEqual(game.move_queue.qsize(), 0)

        print(self.games_persp.cur_gmwidg().gamemodel)

        self.assertEqual(self.games_persp.cur_gmwidg().gamemodel.ply, 4)

    def test2(self):
        """ Test manual examine lecturebot lec2 """

        lines = [
            # examine
            BLOCK_START + '62' + BLOCK_SEPARATOR + '36' + BLOCK_SEPARATOR,
            'Starting a game in examine (scratch) mode.',
            '',
            '<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 77 gbtami gbtami 2 0 0 39 39 0 0 1 none (0:00.000) none 0 0 0',
            'fics% ',
            BLOCK_END,
        ]

        signal = 'exGameCreated'

        game = FICSGame(
            FICSPlayer("gbtami"),
            FICSPlayer("gbtami"),
            gameno=77)
        game = self.connection.games.get(game)
        expectedResults = (game, )
        self.runAndAssertEquals(signal, lines, expectedResults)

        print(self.games_persp.cur_gmwidg().gamemodel)

        lines = [
            # bsetup
            BLOCK_START + '63' + BLOCK_SEPARATOR + '21' + BLOCK_SEPARATOR,
            "Entering setup mode.",
            'fics% ',
            BLOCK_END,
            # bsetup fen r1bq2k1/2p2p1p/p1pp2pB/2n4r/8/2N2Q2/PPP2PPP/4RRK1
            BLOCK_START + '64' + BLOCK_SEPARATOR + '21' + BLOCK_SEPARATOR,
            '<12> r-bq--k- --p--p-p p-pp--pB --n----r -------- --N--Q-- PPP--PPP ----RRK- W -1 1 1 1 1 0 77 gbtami gbtami 2 0 0 39 39 0 0 1 none (0:00.000) none 0 0 0',
            'fics% ',
            BLOCK_END,
            # bsetup wcastle none
            BLOCK_START + '65' + BLOCK_SEPARATOR + '21' + BLOCK_SEPARATOR,
            '<12> r-bq--k- --p--p-p p-pp--pB --n----r -------- --N--Q-- PPP--PPP ----RRK- W -1 0 0 1 1 0 77 gbtami gbtami 2 0 0 39 39 0 0 1 none (0:00.000) none 0 0 0',
            'fics% ',
            BLOCK_END,
            # bsetup bcastle none
            BLOCK_START + '66' + BLOCK_SEPARATOR + '21' + BLOCK_SEPARATOR,
            '<12> r-bq--k- --p--p-p p-pp--pB --n----r -------- --N--Q-- PPP--PPP ----RRK- W -1 0 0 0 0 0 77 gbtami gbtami 2 0 0 39 39 0 0 1 none (0:00.000) none 0 0 0',
            'fics% ',
            BLOCK_END,
            # tomove white
            BLOCK_START + '67' + BLOCK_SEPARATOR + '134' + BLOCK_SEPARATOR,
            '<12> r-bq--k- --p--p-p p-pp--pB --n----r -------- --N--Q-- PPP--PPP ----RRK- W -1 0 0 0 0 0 77 gbtami gbtami 2 0 0 39 39 0 0 1 none (0:00.000) none 0 0 0',
            'fics% ',
            BLOCK_END,
            # bsetup done
            BLOCK_START + '68' + BLOCK_SEPARATOR + '21' + BLOCK_SEPARATOR,
            'Game is validated - entering examine mode.',
            '<12> r-bq--k- --p--p-p p-pp--pB --n----r -------- --N--Q-- PPP--PPP ----RRK- W -1 0 0 0 0 0 77 gbtami gbtami 2 0 0 39 39 0 0 1 none (0:00.000) none 0 0 0',
            'fics% ',
            BLOCK_END,
            # wname Honfi
            BLOCK_START + '69' + BLOCK_SEPARATOR + '148' + BLOCK_SEPARATOR,
            '<12> r-bq--k- --p--p-p p-pp--pB --n----r -------- --N--Q-- PPP--PPP ----RRK- W -1 0 0 0 0 0 77 Honfi gbtami 2 0 0 39 39 0 0 1 none (0:00.000) none 0 0 0',
            'fics% ',
            BLOCK_END,
            # bname Sebestyen
            BLOCK_START + '70' + BLOCK_SEPARATOR + '19' + BLOCK_SEPARATOR,
            '<12> r-bq--k- --p--p-p p-pp--pB --n----r -------- --N--Q-- PPP--PPP ----RRK- W -1 0 0 0 0 0 77 Honfi Sebestyen 2 0 0 39 39 0 0 1 none (0:00.000) none 0 0 0',
            'fics% ',
            BLOCK_END,
            # f3f6
            BLOCK_START + '71' + BLOCK_SEPARATOR + '1' + BLOCK_SEPARATOR,
            '<12> r-bq--k- --p--p-p p-pp-QpB --n----r -------- --N----- PPP--PPP ----RRK- B -1 0 0 0 0 1 77 Honfi Sebestyen 2 0 0 39 39 0 0 1 Q/f3-f6 (0:00.000) Qf6 0 0 0',
            'Game 77: gbtami moves: Qf6',
            'fics% ',
            BLOCK_END,
            # d8f6
            BLOCK_START + '72' + BLOCK_SEPARATOR + '1' + BLOCK_SEPARATOR,
            '<12> r-b---k- --p--p-p p-pp-qpB --n----r -------- --N----- PPP--PPP ----RRK- W -1 0 0 0 0 0 77 Honfi Sebestyen 2 0 0 30 39 0 0 2 Q/d8-f6 (0:00.000) Qxf6 0 0 0',
            'Game 119: gbtami moves: Qxf6',
            'fics% ',
            BLOCK_END,
            # e1e8
            BLOCK_START + '73' + BLOCK_SEPARATOR + '1' + BLOCK_SEPARATOR,
            '<12> r-b-R-k- --p--p-p p-pp-qpB --n----r -------- --N----- PPP--PPP -----RK- B -1 0 0 0 0 1 77 Honfi Sebestyen 2 0 0 30 39 0 0 2 R/e1-e8 (0:00.000) Re8# 0 0 0',
            'Game 119: gbtami moves: Re8#',
            'Game 119: Black checkmated 1-0',
            'fics% ',
            BLOCK_END,
        ]

        def coro():
            yield from self.connection.process_lines(lines)
        self.loop.run_until_complete(coro())

        self.assertEqual(game.move_queue.qsize(), 0)

        print(self.games_persp.cur_gmwidg().gamemodel.boards[-1])

        self.assertEqual(self.games_persp.cur_gmwidg().gamemodel.ply, 3)

        lines = [
            # kibitz Example 2:...
            BLOCK_START + '74' + BLOCK_SEPARATOR + '21' + BLOCK_SEPARATOR,
            'gbtami(1719)[77] kibitzes: Example 2: Dementyev vs Karpov, Riga 1971',
            BLOCK_END,
            # bsetup
            BLOCK_START + '75' + BLOCK_SEPARATOR + '21' + BLOCK_SEPARATOR,
            "Entering setup mode.",
            'fics% ',
            BLOCK_END,
            # bsetup fen q3r1k1/4Rp1p/6p1/2Q1B3/P2P4/1r1b3P/5PP1/4R1K1
            BLOCK_START + '76' + BLOCK_SEPARATOR + '21' + BLOCK_SEPARATOR,
            '<12> q---r-k- ----Rp-p ------p- --Q-B--- P--P---- -r-b---P -----PP- ----R-K- B -1 0 0 0 0 0 77 Honfi Sebestyen 2 0 0 30 39 0 0 1 none (0:00.000) none 0 0 0',
            'fics% ',
            BLOCK_END,
            # bsetup wcastle none
            BLOCK_START + '77' + BLOCK_SEPARATOR + '21' + BLOCK_SEPARATOR,
            '<12> q---r-k- ----Rp-p ------p- --Q-B--- P--P---- -r-b---P -----PP- ----R-K- B -1 0 0 0 0 0 77 Honfi Sebestyen 2 0 0 30 39 0 0 1 none (0:00.000) none 0 0 0',
            'fics% ',
            BLOCK_END,
            # bsetup bcastle none
            BLOCK_START + '78' + BLOCK_SEPARATOR + '21' + BLOCK_SEPARATOR,
            '<12> q---r-k- ----Rp-p ------p- --Q-B--- P--P---- -r-b---P -----PP- ----R-K- B -1 0 0 0 0 0 77 Honfi Sebestyen 2 0 0 30 39 0 0 1 none (0:00.000) none 0 0 0',
            'fics% ',
            BLOCK_END,
            # tomove white
            BLOCK_START + '79' + BLOCK_SEPARATOR + '134' + BLOCK_SEPARATOR,
            '<12> q---r-k- ----Rp-p ------p- --Q-B--- P--P---- -r-b---P -----PP- ----R-K- W -1 0 0 0 0 0 77 Honfi Sebestyen 2 0 0 30 39 0 0 1 none (0:00.000) none 0 0 0',
            'fics% ',
            BLOCK_END,
            # bsetup done
            BLOCK_START + '80' + BLOCK_SEPARATOR + '21' + BLOCK_SEPARATOR,
            'Game is validated - entering examine mode.',
            '<12> q---r-k- ----Rp-p ------p- --Q-B--- P--P---- -r-b---P -----PP- ----R-K- W -1 0 0 0 0 0 77 Honfi Sebestyen 2 0 0 30 39 0 0 1 none (0:00.000) none 0 0 0',
            'fics% ',
            BLOCK_END,
            # wname Dementyev
            BLOCK_START + '81' + BLOCK_SEPARATOR + '148' + BLOCK_SEPARATOR,
            '<12> q---r-k- ----Rp-p ------p- --Q-B--- P--P---- -r-b---P -----PP- ----R-K- W -1 0 0 0 0 0 77 Dementyev Sebestyen 2 0 0 30 39 0 0 1 none (0:00.000) none 0 0 0',
            'fics% ',
            BLOCK_END,
            # bname Karpov
            BLOCK_START + '82' + BLOCK_SEPARATOR + '19' + BLOCK_SEPARATOR,
            '<12> q---r-k- ----Rp-p ------p- --Q-B--- P--P---- -r-b---P -----PP- ----R-K- W -1 0 0 0 0 0 77 Dementyev Karpov 2 0 0 30 39 0 0 1 none (0:00.000) none 0 0 0',
            'fics% ',
            BLOCK_END,
            # c5d5
            BLOCK_START + '83' + BLOCK_SEPARATOR + '1' + BLOCK_SEPARATOR,
            '<12> q---r-k- ----Rp-p ------p- ---QB--- P--P---- -r-b---P -----PP- ----R-K- B -1 0 0 0 0 1 77 Dementyev Karpov 2 0 0 30 39 0 0 1 Q/c5-d5 (0:00.000) Qd5 0 0 0',
            'Game 119: gbtami moves: Qd5',
            'fics% ',
            BLOCK_END,
        ]

        def coro():
            yield from self.connection.process_lines(lines)
        self.loop.run_until_complete(coro())

        self.assertEqual(game.move_queue.qsize(), 0)

        print(self.games_persp.cur_gmwidg().gamemodel.boards[1])

        self.assertEqual(self.games_persp.cur_gmwidg().gamemodel.ply, 1)


if __name__ == '__main__':
    unittest.main()

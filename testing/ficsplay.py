import asyncio
import logging
import unittest

from pychess.Utils.const import FEN_START, WON_MATE, G8, F6
from pychess.Utils.Move import Move
from pychess.Utils.lutils.lmovegen import newMove
from pychess.System import uistuff
from pychess.widgets import gamewidget
from pychess.perspectives import perspective_manager
from pychess.perspectives.fics import FICS
from pychess.perspectives.games import Games
from pychess.perspectives.welcome import Welcome
from pychess.ic.FICSObjects import FICSBoard, FICSGame, GAME_TYPES, TYPE_BLITZ, TYPE_LIGHTNING
from pychess.ic import BLOCK_START, BLOCK_SEPARATOR, BLOCK_END
from ficsmanagers import EmittingTestCase
from pychess.System.Log import log
log.logger.setLevel(logging.DEBUG)

# gbtami commands sent to and lines got from fics:
# bytearray(b'\nChallenge: ggbtami (----) gbtami (1708) unrated blitz 5 0.\nYou can "accept" or "decline", or propose different parameters.\nfics% \n<pf> 7 w=ggbtami t=match p=ggbtami (----) gbtami (1708) unrated blitz 5 0\nfics% ')
# accept 7
# bytearray(b'\x1552\x1611\x16You accept the match offer from ggbtami.\n\n<pr> 7\nfics% \nCreating: gbtami (1708) ggbtami (++++) unrated blitz 5 0\n{Game 107 (gbtami vs. ggbtami) Creating unrated blitz match.}\n\n<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 107 gbtami ggbtami 1 5 0 39 39 300000 300000 1 none (0:00.000) none 0 0 0\n\nGame 107: A disconnection will be considered a forfeit.\n\x17\nfics% ')
# f2f3
# bytearray(b'\x1558\x161\x16\n<12> rnbqkbnr pppppppp -------- -------- -------- -----P-- PPPPP-PP RNBQKBNR B -1 1 1 1 1 0 107 gbtami ggbtami -1 5 0 39 39 300000 300000 1 P/f2-f3 (0:00.000) f3 0 0 0\n\x17\nfics% ')
# bytearray(b'\n<12> rnbqkbnr pppp-ppp -------- ----p--- -------- -----P-- PPPPP-PP RNBQKBNR W 4 1 1 1 1 0 107 gbtami ggbtami 1 5 0 39 39 300000 300000 2 P/e7-e5 (0:00.000) e5 0 1 0\n\nfics% ')
# g2g4
# bytearray(b'\x1561\x161\x16\n<12> rnbqkbnr pppp-ppp -------- ----p--- ------P- -----P-- PPPPP--P RNBQKBNR B 6 1 1 1 1 0 107 gbtami ggbtami -1 5 0 39 39 297338 300000 2 P/g2-g4 (0:02.662) g4 0 1 296\n\x17\nfics% ')
# bytearray(b'\n<12> rnb-kbnr pppp-ppp -------- ----p--- ------Pq -----P-- PPPPP--P RNBQKBNR W -1 1 1 1 1 1 107 gbtami ggbtami 1 5 0 39 39 297338 295763 3 Q/d8-h4 (0:04.237) Qh4# 0 1 304\n\nfics% \n{Game 107 (gbtami vs. ggbtami) gbtami checkmated} 0-1\n\nNo ratings adjustment done.\nfics% ')

# ggbtami commands sent to and lines got from fics:
# match gbtami 5
# bytearray(b'\x1554\x1673\x16Issuing: ggbtami (----) gbtami (1708) unrated blitz 5 0.\n\n<pt> 7 w=gbtami t=match p=ggbtami (----) gbtami (1708) unrated blitz 5 0\nfics% \x17\nfics% ')
# bytearray(b'\ngbtami accepts the match offer.\n\n<pr> 7\nfics% \nCreating: gbtami (1708) ggbtami (++++) unrated blitz 5 0\n{Game 107 (gbtami vs. ggbtami) Creating unrated blitz match.}\n\x07\n<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 107 gbtami ggbtami -1 5 0 39 39 300000 300000 1 none (0:00.000) none 1 0 0\nfics% \nGame 107: A disconnection will be considered a forfeit.\nfics% ')
# bytearray(b'\x07\n<12> rnbqkbnr pppppppp -------- -------- -------- -----P-- PPPPP-PP RNBQKBNR B -1 1 1 1 1 0 107 gbtami ggbtami 1 5 0 39 39 300000 300000 1 P/f2-f3 (0:00.000) f3 1 0 0\nfics% ')
# e7e5
# bytearray(b'\x1561\x161\x16\x07\n<12> rnbqkbnr pppp-ppp -------- ----p--- -------- -----P-- PPPPP-PP RNBQKBNR W 4 1 1 1 1 0 107 gbtami ggbtami -1 5 0 39 39 300000 300000 2 P/e7-e5 (0:00.000) e5 1 1 0\n\x17\nfics% ')
# bytearray(b'\x07\n<12> rnbqkbnr pppp-ppp -------- ----p--- ------P- -----P-- PPPPP--P RNBQKBNR B 6 1 1 1 1 0 107 gbtami ggbtami 1 5 0 39 39 297338 300000 2 P/g2-g4 (0:02.662) g4 1 1 296\n\nfics% ')
# d8h4
# bytearray(b'\x1564\x161\x16\x07\n<12> rnb-kbnr pppp-ppp -------- ----p--- ------Pq -----P-- PPPPP--P RNBQKBNR W -1 1 1 1 1 1 107 gbtami ggbtami -1 5 0 39 39 297338 295763 3 Q/d8-h4 (0:04.237) Qh4# 1 1 304\n\n{Game 107 (gbtami vs. ggbtami) gbtami checkmated} 0-1\n\nNo ratings adjustment done.\n\x17\nfics% ')


class PlayGameTests(EmittingTestCase):
    def setUp(self):
        EmittingTestCase.setUp(self)
        self.manager = self.connection.bm

    def test1(self):
        """ From gbtami (player accepting a challenge) point of view """
        lines = [
            "Challenge: ggbtami (----) gbtami (1708) unrated blitz 5 0.",
            'You can "accept" or "decline", or propose different parameters.',
            "fics% ",
            "<pf> 7 w=ggbtami t=match p=ggbtami (----) gbtami (1708) unrated blitz 5 0",
            "fics% ",
            BLOCK_START + '52' + BLOCK_SEPARATOR + '11' + BLOCK_SEPARATOR,
            "You accept the match offer from ggbtami."
            "",
            "",
            "<pr> 7",
            "fics% ",
            "Creating: gbtami (1708) ggbtami (++++) unrated blitz 5 0",
            "{Game 107 (gbtami vs. ggbtami) Creating unrated blitz match.}"
            "",
            "",
            "<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 107 gbtami ggbtami 1 5 0 39 39 300000 300000 1 none (0:00.000) none 0 0 0",
            ""
            ""
            "Game 107: A disconnection will be considered a forfeit.",
            BLOCK_END,
            "fics% '"]

        me = self.connection.players.get('gbtami')
        me.ratings[TYPE_BLITZ] = 1708
        opponent = self.connection.players.get('ggbtami')
        opponent.ratings[TYPE_BLITZ] = 0
        game = FICSGame(me,
                        opponent,
                        gameno=107,
                        rated=False,
                        game_type=GAME_TYPES['blitz'],
                        private=False,
                        minutes=5,
                        inc=0,
                        board=FICSBoard(300000,
                                        300000,
                                        fen=FEN_START))
        me.game = game
        opponent.game = game
        self.runAndAssertEquals("playGameCreated", lines, (game, ))

        lines = [
            BLOCK_START + '58' + BLOCK_SEPARATOR + '1' + BLOCK_SEPARATOR,
            "<12> rnbqkbnr pppppppp -------- -------- -------- -----P-- PPPPP-PP RNBQKBNR B -1 1 1 1 1 0 107 gbtami ggbtami -1 5 0 39 39 300000 300000 1 P/f2-f3 (0:00.000) f3 0 0 0",
            BLOCK_END,
            "fics% ",
            "<12> rnbqkbnr pppp-ppp -------- ----p--- -------- -----P-- PPPPP-PP RNBQKBNR W 4 1 1 1 1 0 107 gbtami ggbtami 1 5 0 39 39 300000 300000 2 P/e7-e5 (0:00.000) e5 0 1 0",
            "fics% ",
            BLOCK_START + '61' + BLOCK_SEPARATOR + '1' + BLOCK_SEPARATOR,
            "<12> rnbqkbnr pppp-ppp -------- ----p--- ------P- -----P-- PPPPP--P RNBQKBNR B 6 1 1 1 1 0 107 gbtami ggbtami -1 5 0 39 39 297338 300000 2 P/g2-g4 (0:02.662) g4 0 1 296",
            BLOCK_END,
            "fics% ",
            "<12> rnb-kbnr pppp-ppp -------- ----p--- ------Pq -----P-- PPPPP--P RNBQKBNR W -1 1 1 1 1 1 107 gbtami ggbtami 1 5 0 39 39 297338 295763 3 Q/d8-h4 (0:04.237) Qh4# 0 1 304",
            "fics% ",
            "{Game 107 (gbtami vs. ggbtami) gbtami checkmated} 0-1",
            "No ratings adjustment done.",
            "fics% "]

        game = self.connection.games[game]

        async def coro():
            await self.connection.process_lines(lines)
        self.loop.run_until_complete(coro())

        self.assertEqual(game.move_queue.qsize(), 4)
        self.assertEqual(game.reason, WON_MATE)

    def test2(self):
        """ From ggbtami (player sending a challenge) point of view """
        lines = [
            BLOCK_START + '54' + BLOCK_SEPARATOR + '73' + BLOCK_SEPARATOR,
            "Issuing: ggbtami (----) gbtami (1708) unrated blitz 5 0.",
            "<pt> 7 w=gbtami t=match p=ggbtami (----) gbtami (1708) unrated blitz 5 0",
            "fics% ",
            BLOCK_END,
            "gbtami accepts the match offer.",
            "<pr> 7",
            "fics% ",
            "Creating: gbtami (1708) ggbtami (++++) unrated blitz 5 0",
            "{Game 107 (gbtami vs. ggbtami) Creating unrated blitz match.}"
            "",
            "",
            "<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 107 gbtami ggbtami 1 5 0 39 39 300000 300000 1 none (0:00.000) none 0 0 0",
            ""
            ""
            "Game 107: A disconnection will be considered a forfeit.",
            BLOCK_END,
            "fics% '"]

        me = self.connection.players.get('gbtami')
        me.ratings[TYPE_BLITZ] = 1708
        opponent = self.connection.players.get('ggbtami')
        opponent.ratings[TYPE_BLITZ] = 0
        game = FICSGame(me,
                        opponent,
                        gameno=107,
                        rated=False,
                        game_type=GAME_TYPES['blitz'],
                        private=False,
                        minutes=5,
                        inc=0,
                        board=FICSBoard(300000,
                                        300000,
                                        fen=FEN_START))
        me.game = game
        opponent.game = game
        self.runAndAssertEquals("playGameCreated", lines, (game, ))

        lines = [
            "<12> rnbqkbnr pppppppp -------- -------- -------- -----P-- PPPPP-PP RNBQKBNR B -1 1 1 1 1 0 107 gbtami ggbtami -1 5 0 39 39 300000 300000 1 P/f2-f3 (0:00.000) f3 0 0 0",
            "fics% ",
            BLOCK_START + '61' + BLOCK_SEPARATOR + '1' + BLOCK_SEPARATOR,
            "<12> rnbqkbnr pppp-ppp -------- ----p--- -------- -----P-- PPPPP-PP RNBQKBNR W 4 1 1 1 1 0 107 gbtami ggbtami 1 5 0 39 39 300000 300000 2 P/e7-e5 (0:00.000) e5 0 1 0",
            BLOCK_END,
            "fics% ",
            "<12> rnbqkbnr pppp-ppp -------- ----p--- ------P- -----P-- PPPPP--P RNBQKBNR B 6 1 1 1 1 0 107 gbtami ggbtami -1 5 0 39 39 297338 300000 2 P/g2-g4 (0:02.662) g4 0 1 296",
            "fics% ",
            BLOCK_START + '64' + BLOCK_SEPARATOR + '1' + BLOCK_SEPARATOR,
            "<12> rnb-kbnr pppp-ppp -------- ----p--- ------Pq -----P-- PPPPP--P RNBQKBNR W -1 1 1 1 1 1 107 gbtami ggbtami 1 5 0 39 39 297338 295763 3 Q/d8-h4 (0:04.237) Qh4# 0 1 304",
            "{Game 107 (gbtami vs. ggbtami) gbtami checkmated} 0-1",
            "No ratings adjustment done.",
            BLOCK_END,
            "fics% "]

        game = self.connection.games[game]

        async def coro():
            await self.connection.process_lines(lines)
        self.loop.run_until_complete(coro())

        self.assertEqual(game.move_queue.qsize(), 4)
        self.assertEqual(game.reason, WON_MATE)

    def test3(self):
        """ Accepting a seek """

        loop = asyncio.get_event_loop()
        loop.set_debug(enabled=True)

        widgets = uistuff.GladeWidgets("PyChess.glade")
        gamewidget.setWidgets(widgets)
        perspective_manager.set_widgets(widgets)

        self.welcome_persp = Welcome()
        perspective_manager.add_perspective(self.welcome_persp)

        self.games_persp = Games()
        perspective_manager.add_perspective(self.games_persp)

        self.fics_persp = FICS()
        perspective_manager.add_perspective(self.fics_persp)
        self.fics_persp.create_toolbuttons()

        self.lounge = perspective_manager.get_perspective("fics")
        self.lounge.open_lounge(self.connection, self.connection, "freechess.org")

        lines = [
            "<s> 11 w=WLTL ti=00 rt=2030  t=1 i=0 r=r tp=lightning c=? rr=0-9999 a=t f=f",
            "fics% ",
            BLOCK_START + "52" + BLOCK_SEPARATOR + "158" + BLOCK_SEPARATOR,
            "<sr> 11 16",
            "fics% ",
            "Creating: WLTL (2030) gbtami (1771) rated lightning 1 0",
            "{Game 85 (WLTL vs. gbtami) Creating rated lightning match.}",
            "",
            "<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 85 WLTL gbtami -1 1 0 39 39 60000 60000 1 none (0:00.000) none 1 0 0\n\nGame 85: A disconnection will be considered a forfeit.",
            BLOCK_END,
            "fics% "]

        me = self.connection.players.get('gbtami')
        me.ratings[TYPE_LIGHTNING] = 1771
        opponent = self.connection.players.get('WLTL')
        opponent.ratings[TYPE_LIGHTNING] = 2030
        game = FICSGame(opponent,
                        me,
                        gameno=85,
                        rated=True,
                        game_type=GAME_TYPES['lightning'],
                        private=False,
                        minutes=1,
                        inc=0,
                        board=FICSBoard(60000,
                                        60000,
                                        fen=FEN_START))
        me.game = game
        opponent.game = game
        self.runAndAssertEquals("playGameCreated", lines, (game, ))

        gamemodel = self.games_persp.cur_gmwidg().gamemodel

        def on_game_started(game):
            p1 = gamemodel.players[1]
            p1.move_queue.put_nowait(Move(newMove(G8, F6)))

        gamemodel.connect("game_started", on_game_started)

        lines = [
            "<12> rnbqkbnr pppppppp -------- -------- -------- -P------ P-PPPPPP RNBQKBNR B -1 1 1 1 1 0 85 WLTL gbtami 1 1 0 39 39 60000 60000 1 P/b2-b3 (0:00.000) b3 1 0 0",
            "fics% "]

        game = self.connection.games[game]

        async def coro():
            await self.connection.process_lines(lines)
        self.loop.run_until_complete(coro())

        self.assertEqual(game.move_queue.qsize(), 0)

        lines = [
            BLOCK_START + "59" + BLOCK_SEPARATOR + "1" + BLOCK_SEPARATOR,
            "<12> rnbqkb-r pppppppp -----n-- -------- -------- -P------ P-PPPPPP RNBQKBNR W -1 1 1 1 1 1 85 WLTL gbtami -1 1 0 39 39 60000 60000 2 N/g8-f6 (0:00.000) Nf6 1 1 0",
            BLOCK_END,
            "fics% ",
            "<12> rnbqkb-r pppppppp -----n-- -------- -------- -P----P- P-PPPP-P RNBQKBNR B -1 1 1 1 1 0 85 WLTL gbtami 1 1 0 39 39 59900 60000 2 P/g2-g3 (0:00.100) g3 1 1 285",
            "fics% "]

        async def coro():
            await self.connection.process_lines(lines)
        self.loop.run_until_complete(coro())

        self.assertEqual(game.move_queue.qsize(), 0)
        self.assertEqual(gamemodel.ply, 3)
        print(gamemodel.boards[-1])


if __name__ == '__main__':
    unittest.main()

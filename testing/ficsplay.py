import unittest

from pychess.Utils.const import FEN_START, WON_MATE
from pychess.ic.FICSObjects import FICSBoard, FICSGame, GAME_TYPES, TYPE_BLITZ
from pychess.ic import BLOCK_START, BLOCK_SEPARATOR, BLOCK_END
from ficsmanagers import EmittingTestCase

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

        def coro():
            yield from self.connection.process_lines(lines)
        self.loop.run_until_complete(coro())

        self.assertEqual(game.wmove_queue.qsize(), 2)
        self.assertEqual(game.bmove_queue.qsize(), 2)
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

        def coro():
            yield from self.connection.process_lines(lines)
        self.loop.run_until_complete(coro())

        self.assertEqual(game.wmove_queue.qsize(), 2)
        self.assertEqual(game.bmove_queue.qsize(), 2)
        self.assertEqual(game.reason, WON_MATE)


if __name__ == '__main__':
    unittest.main()

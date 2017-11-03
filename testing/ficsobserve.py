import unittest

try:
    import faulthandler
    faulthandler.enable()
except:
    pass

from pychess.ic.FICSObjects import FICSPlayer, FICSGame
from pychess.ic import BLOCK_START, BLOCK_SEPARATOR, BLOCK_END
from pychess.System import uistuff
from pychess.widgets import gamewidget
from pychess.perspectives import perspective_manager
from pychess.perspectives.fics import FICS
from pychess.perspectives.games import Games
from ficsmanagers import EmittingTestCase


"""
[Event "FICS rated standard game"]
[Site "freechess.org"]
[White "schachbjm"]
[Black "Maras"]
[TimeControl "2700+45"]
[Result "*"]
[WhiteClock "0:10:53.625"]
[BlackClock "0:05:19.070"]
[WhiteElo "2243"]
[BlackElo "2158"]
[Date "2016.01.23"]
[Time "14:34:00"]
1. e4 {[%emt 0:00:00.000]} e6 {[%emt 0:00:00.000]}
2. d4 {[%emt 0:00:01.617]} d5 {[%emt 0:00:02.220]}
3. Nc3 {[%emt 0:00:00.442]} Nc6 {[%emt 0:00:54.807]}
4. e5 {[%emt 0:00:40.427]} Nge7 {[%emt 0:00:28.205]}
5. Nf3 {[%emt 0:00:21.570]} Nf5 {[%emt 0:00:28.818]}
6. h4 {[%emt 0:01:17.369]} h5 {[%emt 0:04:58.315]}
7. Bg5 {[%emt 0:00:55.946]} Be7 {[%emt 0:04:01.555]}
8. Qd2 {[%emt 0:00:02.434]} b6 {[%emt 0:05:12.110]}
9. O-O-O {[%emt 0:00:59.124]} Bb7 {[%emt 0:00:08.796]}
10. Kb1 {[%emt 0:00:01.900]} Qd7 {[%emt 0:04:39.500]}
11. Bxe7 {[%emt 0:19:59.514]} Qxe7 {[%emt 0:02:42.462]}
12. g3 {[%emt 0:00:58.847]} O-O-O {[%emt 0:00:36.468]}
13. Bh3 {[%emt 0:00:12.284]} Nh6 {[%emt 0:04:06.076]}
14. Ne2 {[%emt 0:00:02.387]} g6 {[%emt 0:05:02.695]}
15. Nf4 {[%emt 0:00:02.976]} Kb8 {[%emt 0:05:26.776]}
16. Rhe1 {[%emt 0:02:33.781]} Na5 {[%emt 0:02:23.956]}
17. b3 {[%emt 0:00:28.817]} Rc8 {[%emt 0:01:09.281]}
18. Ng5 {[%emt 0:08:15.515]} c5 {[%emt 0:05:17.139]}
19. Bxe6 {[%emt 0:12:26.052]} fxe6 {[%emt 0:01:14.670]}
20. Nxg6 {[%emt 0:00:02.168]} Qd7 {[%emt 0:01:23.832]}
21. Nxh8 {[%emt 0:00:02.249]} Rxh8 {[%emt 0:00:04.212]}
22. dxc5 {[%emt 0:00:14.456]} Nf5 {[%emt 0:00:24.046]}
23. cxb6 {[%emt 0:00:07.092]} axb6 {[%emt 0:00:03.296]}
24. Qb4 {[%emt 0:00:42.800]} Qc6 {[%emt 0:02:48.991]}
25. Nf7 {[%emt 0:02:09.657]} Rc8 {[%emt 0:00:37.030]}
26. Rd2 {[%emt 0:00:01.602]} Qc5 {[%emt 0:05:03.082]}
27. Qxc5 {[%emt 0:00:09.672]} bxc5 {[%emt 0:00:00.100]}
28. Nd6 {[%emt 0:00:00.849]} Rf8 {[%emt 0:00:04.101]}
29. c3 {[%emt 0:00:57.437]} Kc7 {[%emt 0:03:05.263]}
30. Nxf5 {[%emt 0:01:51.872]} Rxf5 {[%emt 0:00:00.100]}
31. f4 {[%emt 0:00:00.603]} Bc6 {[%emt 0:01:06.696]}
32. Kc2 {[%emt 0:00:01.613]} Be8 {[%emt 0:00:07.670]}
33. Kd3 {[%emt 0:01:39.823]} Rf8 {[%emt 0:01:28.227]}
34. Ke3 {[%emt 0:00:06.207]} Bg6 {[%emt 0:00:08.648]}
35. Rc1 {[%emt 0:03:24.100]} Bf5 {[%emt 0:01:11.762]}
36. Rb2 {[%emt 0:00:13.173]} Rb8 {[%emt 0:00:10.025]}
*
"""


class ObserveGameTests(EmittingTestCase):
    def setUp(self):
        EmittingTestCase.setUp(self)
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

    def test1(self):
        """ Test observing game """

        lines = [
            "{Game 463 (schachbjm vs. Maras) Creating rated standard match.}",
            BLOCK_START + '34' + BLOCK_SEPARATOR + '80' + BLOCK_SEPARATOR,
            'You are now observing game 463.',
            'Game 463: schachbjm (2243) Maras (2158E) rated standard 45 45',
            '',
            '<12> -r------ --k----- ----p--- n-ppPb-p -----P-P -PP-K-P- PR------ --R----- W -1 0 0 0 0 11 463 schachbjm Maras 0 45 45 17 15 557871 274070 37 R/f8-b8 (0:10.025) Rb8 0 1 0',
            BLOCK_END
        ]

        def coro():
            yield from self.connection.process_lines(lines)
        self.loop.run_until_complete(coro())

        self.assertEqual(self.connection.client.commands[-1], "moves 463")

        signal = 'obsGameCreated'
        lines = [
            'Movelist for game 463:',
            '',
            'schachbjm (2243) vs. Maras (2158) --- Sat Jan 23, 14:34 EST 2016',
            'Rated standard match, initial time: 45 minutes, increment: 45 seconds.',
            '',
            'Move  schachbjm               Maras',
            '----  ---------------------   ---------------------',
            '1.  e4      (0:00.000)      e6      (0:00.000)',
            '2.  d4      (0:01.617)      d5      (0:02.220)',
            '3.  Nc3     (0:00.442)      Nc6     (0:54.807)',
            '4.  e5      (0:40.427)      Nge7    (0:28.205)',
            '5.  Nf3     (0:21.570)      Nf5     (0:28.818)',
            '6.  h4      (1:17.369)      h5      (4:58.315)',
            '7.  Bg5     (0:55.946)      Be7     (4:01.555)',
            '8.  Qd2     (0:02.434)      b6      (5:12.110)',
            '9.  O-O-O   (0:59.124)      Bb7     (0:08.796)',
            '10.  Kb1     (0:01.900)      Qd7     (4:39.500)',
            '11.  Bxe7    (19:59.514)     Qxe7    (2:42.462)',
            '12.  g3      (0:58.847)      O-O-O   (0:36.468)',
            '13.  Bh3     (0:12.284)      Nh6     (4:06.076)',
            '14.  Ne2     (0:02.387)      g6      (5:02.695)',
            '15.  Nf4     (0:02.976)      Kb8     (5:26.776)',
            '16.  Rhe1    (2:33.781)      Na5     (2:23.956)',
            '17.  b3      (0:28.817)      Rc8     (1:09.281)',
            '18.  Ng5     (8:15.515)      c5      (5:17.139)',
            '19.  Bxe6    (12:26.052)     fxe6    (1:14.670)',
            '20.  Nxg6    (0:02.168)      Qd7     (1:23.832)',
            '21.  Nxh8    (0:02.249)      Rxh8    (0:04.212)',
            '22.  dxc5    (0:14.456)      Nf5     (0:24.046)',
            '23.  cxb6    (0:07.092)      axb6    (0:03.296)',
            '24.  Qb4     (0:42.800)      Qc6     (2:48.991)',
            '25.  Nf7     (2:09.657)      Rc8     (0:37.030)',
            '26.  Rd2     (0:01.602)      Qc5     (5:03.082)',
            '27.  Qxc5    (0:09.672)      bxc5    (0:00.100)',
            '28.  Nd6     (0:00.849)      Rf8     (0:04.101)',
            '29.  c3      (0:57.437)      Kc7     (3:05.263)',
            '30.  Nxf5    (1:51.872)      Rxf5    (0:00.100)',
            '31.  f4      (0:00.603)      Bc6     (1:06.696)',
            '32.  Kc2     (0:01.613)      Be8     (0:07.670)',
            '33.  Kd3     (1:39.823)      Rf8     (1:28.227)',
            '34.  Ke3     (0:06.207)      Bg6     (0:08.648)',
            '35.  Rc1     (3:24.100)      Bf5     (1:11.762)',
            '36.  Rb2     (0:13.173)      Rb8     (0:10.025)',
            '{Still in progress} *',
        ]

        game = FICSGame(
            FICSPlayer("schachbjm"),
            FICSPlayer("Maras"),
            gameno=463)
        game = self.connection.games.get(game)
        expectedResults = (game, )
        self.runAndAssertEquals(signal, lines, expectedResults)

        print(self.games_persp.cur_gmwidg().gamemodel)

        lines = [
            '<12> -r------ --k----- ----p--- n-ppPb-p -----P-P -PP-K-P- PR------ ------R- B -1 0 0 0 0 11 463 schachbjm Maras 0 45 45 17 15 557871 274070 37 R/b2-g2 (0:10.025) Rg2 0 1 0',
            '<12> ------r- --k----- ----p--- n-ppPb-p -----P-P -PP-K-P- PR------ ------R- W -1 0 0 0 0 11 463 schachbjm Maras 0 45 45 17 15 557871 274070 38 R/b8-g8 (0:10.025) Rg8 0 1 0',
        ]

        def coro():
            yield from self.connection.process_lines(lines)
        self.loop.run_until_complete(coro())

        self.assertEqual(game.wmove_queue.qsize(), 0)
        self.assertEqual(game.bmove_queue.qsize(), 0)

        self.assertEqual(self.games_persp.cur_gmwidg().gamemodel.ply, 74)

        print(self.games_persp.cur_gmwidg().gamemodel)


if __name__ == '__main__':
    unittest.main()

import unittest
import random

from pychess.Savers.remotegame import InternetGameLichess, InternetGameChessgames, InternetGameFicsgames, InternetGameChesstempo, InternetGameChess24, InternetGame365chess, InternetGameChesspastebin, InternetGameChessbomb, InternetGameGeneric, get_internet_game_as_pgn


class RemoteGameTestCase(unittest.TestCase):
    def executeTest(self, cp, links):
        # Check
        if cp is None or links is None or len(links) == 0:
            return
        print("\n%s" % cp.get_description())

        # Pick one link only to not overload the remote server
        url, expected = random.choice(links)
        print('- Target link : %s' % url)
        print('- Expecting data : %s' % expected)

        # Download link
        data = get_internet_game_as_pgn(url)
        ok = data is not None
        print('- Fetched data : %s' % ok)
        self.assertEqual(ok, expected)

    def testLichess(self):
        links = [('http://lichess.org/CA4bR2b8/black/analysis#12', True),       # Game in advanced position
                 ('https://lichess.org/CA4bR2b8', True),                        # Canonical address
                 ('https://lichess.org/game/export/CA4bR2b8', True),            # Download link
                 ('http://fr.lichess.org/@/thibault', False),                   # Not a game (user page)
                 ('http://lichess.org/blog', False),                            # Not a game (page)
                 ('http://lichess.dev/ABCD1234', False),                        # Not a game (wrong ID)
                 ('https://LICHESS.org/nGhOUXdP?p=0', True),                    # Variant game with parameter
                 ('https://lichess.org/nGhOUXdP?p=0#3', True),                  # Variant game with parameter and anchor
                 ('https://hu.lichess.org/study/hr4H7sOB?page=1', True),        # Study of one game with unused parameter
                 ('https://lichess.org/study/hr4H7sOB/fvtzEXvi.pgn#32', True),  # Chapter of a study with anchor
                 ('https://lichess.org/STUDY/hr4H7sOB.pgn', True)]              # Study of one game
        self.executeTest(InternetGameLichess(), links)

    def testChessgames(self):
        links = [('http://www.chessgames.com/perl/chessgame?gid=1075462&comp=1', True),         # With computer analysis
                 ('http://www.chessgames.com/perl/chessgame?gid=1075463', True),                # Without computer analysis
                 ('http://www.CHESSGAMES.com/perl/chessgame?gid=1075463&comp=1#test', True),    # Without computer analysis but requested in URL
                 ('http://www.chessgames.com/perl/chessgame?gid=1234567890', False)]            # Not a game
        self.executeTest(InternetGameChessgames(), links)

    def testFicsgames(self):
        links = [('https://www.ficsgames.org/cgi-bin/show.cgi?ID=451813954;action=save', True), # Normal game
                 ('https://www.ficsgames.org/cgi-bin/show.cgi?ID=qwertz;action=save', True),    # Invalid identifier (not numeric)
                 ('https://www.ficsgames.org/cgi-bin/show.cgi?ID=0#anchor', False),             # Invalid identifier (null)
                 ('https://www.ficsgames.org/about.html', False)]                               # Not a game
        self.executeTest(InternetGameFicsgames(), links)

    def testChesstempo(self):
        links = [('https://chesstempo.com/gamedb/game/2046457', True),                  # Game
                 ('https://chesstempo.com/gamedb/game/2046457/foo/bar/123', True),      # Game with additional path
                 ('https://www.chesstempo.com/gamedb/game/2046457?p=0#tag', True),      # Game with additional parameters
                 ('http://chesstempo.com/faq.html', False)]                             # Not a game
        self.executeTest(InternetGameChesstempo(), links)

    def testChess24(self):
        links = [('https://chess24.com/en/game/DQhOOrJaQKS31LOiOmrqPg#anchor', True)]   # Game with anchor
        self.executeTest(InternetGameChess24(), links)

    def test365chess(self):
        links = [('https://www.365chess.com/view_game.php?g=4187437#anchor', True),     # Game 1/2-1/2 for special chars
                 ('https://www.365chess.com/view_game.php?g=1234567890', False)]        # Not a game
        self.executeTest(InternetGame365chess(), links)

    def testChesspastebin(self):
        links = [('https://www.chesspastebin.com/2018/12/29/anonymous-anonymous-by-george-2/', True),       # Game quite complete
                 ('https://www.chesspastebin.com/2019/04/14/unknown-unknown-by-alekhine-sapladi/', True),   # Game with no header
                 ('https://www.chesspastebin.com', False)]                                                  # Homepage
        self.executeTest(InternetGameChesspastebin(), links)

    def testChessbomb(self):
        links = [('https://www.chessbomb.com/arena/2019-katowice-chess-festival-im/04-Kubicka_Anna-Sliwicka_Alicja', True),     # Game
                 ('https://www.chessbomb.com/arena/2019-bangkok-chess-open', False)]                                            # Not a game (arena)
        self.executeTest(InternetGameChessbomb(), links)

    def testGeneric(self):
        links = None
        self.executeTest(InternetGameGeneric(), links)


if __name__ == '__main__':
    unittest.main()

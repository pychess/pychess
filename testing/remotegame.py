import unittest
import random

from pychess.Savers.remotegame import chess_providers, get_internet_game_as_pgn


class RemoteGameTestCase(unittest.TestCase):
    def test(self):
        for cp in chess_providers:
            print("\n%s" % cp.get_description())

            # Pick one link only to not overload the remote server
            list = cp.get_test_links()
            if list is None or len(list) == 0:
                continue
            url, expected = random.choice(list)
            print('- Target link : %s' % url)
            print('- Expecting data : %s' % expected)

            # Download link
            data = get_internet_game_as_pgn(url)
            ok = not data is None
            print('- Fetched data : %s' % ok)
            self.assertEqual(ok, expected)


if __name__ == '__main__':
    unittest.main()

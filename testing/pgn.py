
import unittest

from pychess.Savers.pgn import load, walk, pattern, MOVE
from pychess.System.protoopen import protoopen


file_names = ("atomic", "chess960rwch", "world_matches", "zh")
file_handles = []
for name in file_names:
    file_handles.append(protoopen("gamefiles/%s.pgn" % name))


class PgnTestCase(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        for handle in file_handles:
            handle.close()

    def test_movre(self):
        """Testing SAN pattern regexp"""
        moves = "e4 fxg7 g8=Q gxh8=N a2+ axb1# c1=Q+ exd8=N# " + \
            "0-0-0 O-O-O 0-0 O-O Ka1 Kxf8 Kxd4+ " + \
            "Qc3 Rxh8 B1xg7 Nhxg2 Qe4xd5 Rb7+ Bxg4# N8xb2+ Qaxb7# Qd5xe4+"
        matches = [m[MOVE - 1] for m in pattern.findall(moves)]
        self.assertEqual(' '.join(matches), ' '.join(moves.split()))


def create_test(o, n):
    def test_expected(self):
        for orig, new in zip(o.split(), n.split()):
            # Seems most .PGN unnecessary contains unambiguous notation
            # when second move candidate is invalid (leaves king in check)
            # f.e.: 1.e4 e5 2.d4 Nf6 3.Nc3 Bb4 Nge2
            if len(orig) == len(new) + 1 and orig[0] == new[0] and orig[2:] == new[1:]:
                continue

            elif orig[-1] in "?!" and new[-1] not in "?!":
                # pgn export format uses nag
                break

            elif (orig == "0-0" and new == "O-O") or (orig == "0-0-0" and new == "O-O-O"):
                continue

            self.assertEqual(orig, new)

    return test_expected


def normalize(text):
    text = text.splitlines()
    text = " ".join(text)
    text = text.replace('.   ', '. ').replace('.  ', '. ')
    text = text.replace('  )', ')').replace(' )', ')')
    text = text.replace('(  ', '(').replace('( ', '(')
    text = text.replace('  }', '}').replace(' }', '}')
    text = text.replace('{  ', '{').replace('{ ', '{')
    return text


for j, name in enumerate(file_names):
    print("Creating test methods for %s" % name)
    pgnfile = load(file_handles[j])
    pgnfile.limit = 1000
    pgnfile.init_tag_database()
    games, plys = pgnfile.get_records()

    for i, game in enumerate(games):
        print("%s/%s" % (i + 1, pgnfile.get_count()))
        orig = normalize(pgnfile.get_movetext(game))

        model = pgnfile.loadToModel(game)
        new = []
        walk(model.boards[0].board, new, model)
        new = normalize(" ".join(new))

        # create test method
        test_method = create_test(orig, new)

        # change it's name to be unique in PgnTestCase class
        test_method.__name__ = 'test_%s_%d' % (name, i + 1)
        test_method.__doc__ = "Pgn read-write %s" % ' '.join(test_method.__name__.split('_'))

        # monkey patch PgnTestCase class, adding the new test method
        setattr(PgnTestCase, test_method.__name__, test_method)


if __name__ == '__main__':
    unittest.main()

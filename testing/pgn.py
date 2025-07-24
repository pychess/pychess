import os.path
import unittest

from pychess.Savers.pgn import load, walk, pattern, MOVE
from pychess.System.protoopen import protoopen


def normalize(text):
    text = text.splitlines()
    text = " ".join(text)
    text = text.replace(".   ", ". ").replace(".  ", ". ")
    text = text.replace("  )", ")").replace(" )", ")")
    text = text.replace("(  ", "(").replace("( ", "(")
    text = text.replace("  }", "}").replace(" }", "}")
    text = text.replace("{  ", "{").replace("{ ", "{")
    return text


class PgnRegexpTestCase(unittest.TestCase):
    def test_movre(self):
        """Testing SAN pattern regexp"""
        moves = (
            "e4 fxg7 g8=Q gxh8=N a2+ axb1# c1=Q+ exd8=N# "
            + "0-0-0 O-O-O 0-0 O-O Ka1 Kxf8 Kxd4+ "
            + "Qc3 Rxh8 B1xg7 Nhxg2 Qe4xd5 Rb7+ Bxg4# N8xb2+ Qaxb7# Qd5xe4+"
        )
        matches = [m[MOVE - 1] for m in pattern.findall(moves)]
        self.assertEqual(" ".join(matches), " ".join(moves.split()))


class PgnTestCase(unittest.TestCase):
    def pgn_test(self, name):
        curdir = os.path.dirname(__file__)
        pgnfile = load(protoopen("%s/gamefiles/%s.pgn" % (curdir, name)))
        pgnfile.limit = 1000
        pgnfile.init_tag_database()
        games, plys = pgnfile.get_records()

        for i, game in enumerate(games):
            print(f"{i + 1}/{pgnfile.get_count()}")
            orig_moves_text = normalize(pgnfile.get_movetext(game))

            model = pgnfile.loadToModel(game)
            print(model.tags["Site"])
            new_moves = []
            walk(model.boards[0].board, new_moves, model)
            new_moves_text = normalize(" ".join(new_moves))

            for orig, new in zip(orig_moves_text.split(), new_moves_text.split()):
                # Seems most .PGN unnecessary contains unambiguous notation
                # when second move candidate is invalid (leaves king in check)
                # f.e.: 1.e4 e5 2.d4 Nf6 3.Nc3 Bb4 Nge2
                if (
                    len(orig) == len(new) + 1
                    and orig[0] == new[0]
                    and orig[2:] == new[1:]
                ):
                    continue

                elif orig[-1] in "?!" and new[-1] not in "?!":
                    # pgn export format uses nag
                    break

                elif (orig == "0-0" and new == "O-O") or (
                    orig == "0-0-0" and new == "O-O-O"
                ):
                    continue

                self.assertEqual(orig, new)

        pgnfile.close()

    def test_pgn(self):
        self.pgn_test("atomic")
        self.pgn_test("chess960rwch")
        self.pgn_test("world_matches")
        self.pgn_test("zh")
        self.pgn_test("sittuyin")
        self.pgn_test("schess")


if __name__ == "__main__":
    unittest.main()

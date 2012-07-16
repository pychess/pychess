import sys
import unittest

from pychess.Utils.Board import Board
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Savers.pgn import load, walk
from pychess.Savers.pgnbase import pattern, MOVE
from pychess.Utils.const import *


class PgnTestCase(unittest.TestCase):
    def test_movre(self):
        """Testing SAN pattern regexp"""
        moves = "e4 fxg7 g8=Q gxh8=N a2+ axb1# c1=Q+ exd8=N# "+ \
                "0-0-0 O-O-O 0-0 O-O Ka1 Kxf8 Kxd4+ "+ \
                "Qc3 Rxh8 B1xg7 Nhxg2 Qe4xd5 Rb7+ Bxg4# N8xb2+ Qaxb7# Qd5xe4+"
        matches = [m[MOVE-1] for m in pattern.findall(moves)] 
        self.assertEqual(' '.join(matches), ' '.join(moves.split()))

def create_test(lines, result, gameno):
    def test_expected(self):
        for orig, new in zip(lines.split(), result.split()):
            # Seems most .PGN unnecessary contains unambiguous notation
            # when second move candidate is invalid (leaves king in check)
            # f.e.: 1.e4 e5 2.d4 Nf6 3.Nc3 Bb4 Nge2
            if len(orig) == len(new)+1 and orig[0] == new[0] and orig[2:] == new[1:]:
                continue

            if orig[-1] in "?!" and new[-1] not in "?!":
                # pgn export format uses nag
                break
            elif orig == "0-0" or orig == "0-0-0":
                continue

            self.assertEqual(orig, new)

    return test_expected

#PgnFile = load(open('/home/tamas/PGN/russian_chess.pgn'))
#PgnFile = load(open('/home/tamas/PGN/kasp_top.pgn'))
#PgnFile = load(open('/home/tamas/PGN/hartwig.pgn'))
PgnFile = load(open('gamefiles/world_matches.pgn'))
for i, game in enumerate(PgnFile.games):
    print "%s/%s" % (i+1, len(PgnFile.games))

    model = PgnFile.loadToModel(i)
    result = []
    walk(model.boards[0], result)
    result = " ".join(result)
    status = reprResult[model.status]
    
    lines = game[1].replace('.   ', '. ').replace('.  ', '. ')
    lines = lines.replace('\r\n', ' ')
    lines = lines.replace('  )', ')').replace(' )', ')')
    lines = lines.replace('(  ', '(').replace('( ', '(')
    lines = lines.replace('  }', '}').replace(' }', '}')
    lines = lines.replace('{  ', '{').replace('{ ', '{')
    lines = lines.replace('(\r\n', '(').replace('\r\n)', ')')
    lines = lines.replace('{\r\n', '{').replace('\r\n}', '}')
    lines = lines.splitlines()
    lines = [line.strip() for line in lines]
    lines = ' '.join(lines)
    result = "%s %s" % (result, status)

    test_method = create_test(lines, result, i)
    test_method.__name__ = 'test_game_%d' % (i+1)
    setattr (PgnTestCase, test_method.__name__, test_method)


if __name__ == '__main__':
    unittest.main()

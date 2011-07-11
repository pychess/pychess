import sys
import unittest

from pychess.Utils.Board import Board
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Savers.pgn import load, walk, movre
from pychess.Utils.const import *


class PgnTestCase(unittest.TestCase):
    
    def setUp(self):
        self.PgnFile = load(open('gamefiles/world_matches.pgn'))

    def testPGN(self):
        """Testing pgn file"""
        for i, game in enumerate(self.PgnFile.games):
            print i
            if i in (20, 109, 111, 157, 195, 197, 229) or i>229:
                #20 is chaotic
                #109 8. Nge2 is unnecessary, koz Nce2 leaves the king in check
                #111 10. Nde2 (same)
                #157 6. Nge2 (same)
                #229 two comments for a move and a variation between them
                # TODO: analyse remaining failures (i>229)
                continue

            model = self.PgnFile.loadToModel(i, quick_parse=False)
            result = []
            walk(model.boards[0], result)
            result = " ".join(result)
            status = reprResult[model.status]
            
            lines = game[1].replace('(\r\n', '(').replace('\r\n)', ')')
            lines = lines.replace('{\r\n', '{').replace('\r\n}', '}')
            lines = lines.splitlines()
            lines = [line.strip() for line in lines]
            self.assertEqual(' '.join(lines), "%s %s" % (result, status))
    
    def testMovre(self):
        """Testing movre regexp"""
        moves = "e4 fxg7 g8=Q gxh8=N a2+ axb1# c1=Q+ exd8=N# "+ \
                "0-0-0 O-O-O 0-0 O-O Ka1 Kxf8 Kxd4+ "+ \
                "Qc3 Rxh8 B1xg7 Nhxg2 Qe4xd5 Rb7+ Bxg4# N8xb2+ Qaxb7# Qd5xe4+"
        
        self.assertEqual(' '.join(movre.findall(moves)), ' '.join(moves.split()))

if __name__ == '__main__':
    unittest.main()

import sys
import unittest

import __builtin__
__builtin__.__dict__['_'] = lambda s: s

from pychess.Utils.Board import Board
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Savers import pgn
from pychess.Utils.const import FEN_START


KEEPENDS = True

GAMES = """
[Event "Bourdonnais"]
[Site "La Palamede 1837"]
[Date "1797.??.??"]
[Round "?"]
[White "De la Bourdonnais, Louis"]
[Black "?"]
[Result "1-0"]
[Annotator "JvR"]
[SetUp "1"]
[FEN "8/2P1k3/8/5Q2/8/3pp3/4rp2/3K4 w - - 0 1"]
[PlyCount "11"]
[EventDate "1797.??.??"]

{De la Bourdonnais (1797-1840) played a series of six matches with MacDonnell
in London 1834. It was the first long international chess event. The tactical
talent of the Frenchman prevailed. He composed a simple endgame study.} 1.
c8=N+ $1 {Calvi and De la Bourdonnais supported the idea of minor promotion as
a law of chess.} (1. Qh7+ $2 Kf6 $1 {leads to a repetition of moves.}) 1... Ke8
2. Qg6+ Kf8 3. Qf6+ Kg8 4. Ne7+ Kh7 5. Qg6+ Kh8 6. Qg8# 1-0

[Event "Horwitz"]
[Site "Chess Studies 1851"]
[Date "1807.??.??"]
[Round "?"]
[White "Kling & Horwitz"]
[Black "?"]
[Result "1-0"]
[Annotator "JvR"]
[SetUp "1"]
[FEN "3N4/2p5/8/3q4/3k4/8/3PKP2/R7 w - - 0 1"]
[PlyCount "9"]
[EventDate "1807.??.??"]

{Bernhard Horwitz (1807-1885) moved from Germany to London in 1846. Staunton
defeated him in a match. He cooperated with the chess composer Josef Kling.
Endgame composition began with their joined effort.} 1. Ra4+ Ke5 2. Ra5 $1 c5 (
2... Qxa5 3. Nc6+) 3. Rxc5 $1 Qxc5 4. d4+ $1 Kxd4 (4... Qxd4 5. Nc6+) 5. Ne6+ {
A fork decides the game in three variations.} 1-0
"""

MOVES = [
["c7c8", "e7e8", "f5g6", "e8f8", "g6f6", "f8g8", "c8e7", "g8h7", "f6g6", "h7h8", "g6g8"],
["a1a4", "d4e5", "a4a5", "c7c5", "a5c5", "d5c5", "d2d4", "e5d4", "d8e6"],
]


class PgnTestCase(unittest.TestCase):
    
    def setUp(self):
        self.PgnFile = pgn.load(GAMES.splitlines(KEEPENDS))

    def testPGN(self):
        """Testing pgn file"""
        print
        for i, game in enumerate(self.PgnFile.games):
            sys.stdout.write("#")
            model = self.PgnFile.loadToModel(i, -1)
            self.assertEqual(map(repr, model.moves), MOVES[i])
        print
            
if __name__ == '__main__':
    unittest.main()

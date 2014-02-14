# Corner Chess

import random

from pychess.Utils.const import *
from pychess.Utils.Board import Board

class CornerBoard(Board):
    variant = CORNERCHESS

    def __init__ (self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=self.shuffle_start(), lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

    def shuffle_start(self):
        b1 = b2 = 0
        tmp = ['r', 'n', 'b', 'q', 'b', 'n', 'r']
        while (b1%2 == b2%2):
            random.shuffle(tmp)
            b1 = tmp.index('b')
            b2 = tmp.index('b', b1+1)
        tmp = ''.join(tmp)
        tmp = 'k' + tmp + '/pppppppp/8/8/8/8/PPPPPPPP/' + tmp[::-1].upper() + 'K w - - 0 1'
        
        return tmp

class CornerChess:
    __desc__ = \
        _("http://brainking.com/en/GameRules?tp=2\n" +
          "* Placement of the pieces on the 1st and 8th row are randomized\n" +
          "* The king is in the right hand corner\n" +
          "* Bishops must start on opposite color squares\n" +
          "* Black's starting position is obtained by rotating white's position 180 degrees around the board's center\n" +
          "* No castling")
    name = _("Corner")
    cecp_name = "nocastle"
    board = CornerBoard
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_SHUFFLE


if __name__ == '__main__':
    Board = CornerBoard(True)
    for i in range(10):
        print Board.shuffle_start()

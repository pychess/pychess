from __future__ import print_function
# Corner Chess

import random

from pychess.Utils.const import VARIANTS_SHUFFLE, CORNERCHESS
from pychess.Utils.Board import Board


class CornerBoard(Board):
    variant = CORNERCHESS
    __desc__ = \
        _("http://brainking.com/en/GameRules?tp=2\n" +
          "* Placement of the pieces on the 1st and 8th row are randomized\n" +
          "* The king is in the right hand corner\n" +
          "* Bishops must start on opposite color squares\n" +
          "* Black's starting position is obtained by rotating white's position 180 degrees around the board's center\n" +
          "* No castling")
    name = _("Corner")
    cecp_name = "nocastle"
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_SHUFFLE

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=self.shuffle_start(), lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

    def shuffle_start(self):
        set1 = set2 = 0
        back_rank = ['r', 'n', 'b', 'q', 'b', 'n', 'r']
        while set1 % 2 == set2 % 2:
            random.shuffle(back_rank)
            set1 = back_rank.index('b')
            set2 = back_rank.index('b', set1 + 1)
        fen = ''.join(back_rank)
        fen = 'k' + fen + '/pppppppp/8/8/8/8/PPPPPPPP/' + fen[::-1].upper(
        ) + 'K w - - 0 1'

        return fen


if __name__ == '__main__':
    Board = CornerBoard(True)
    for i in range(10):
        print(Board.shuffle_start())

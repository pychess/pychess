""" Shuffle Variant"""
from __future__ import print_function

import random

from pychess.Utils.const import SHUFFLECHESS, VARIANTS_SHUFFLE
from pychess.Utils.Board import Board


class ShuffleBoard(Board):
    """:Description: The shuffle variant uses the standard chess rules with the exception
        no castling is allowed and the back rank is shuffled around
    """
    variant = SHUFFLECHESS
    __desc__ = _(
        "xboard nocastle: http://home.hccnet.nl/h.g.muller/engine-intf.html#8\n" +
        "FICS wild/2: http://www.freechess.org/Help/HelpFiles/wild.html\n" +
        "* Random arrangement of the pieces behind the pawns\n" +
        "* No castling\n" + "* Black's arrangement mirrors white's")
    name = _("Shuffle")
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
        back_rank = ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r']
        random.shuffle(back_rank)
        fen = ''.join(back_rank)
        fen = fen + '/pppppppp/8/8/8/8/PPPPPPPP/' + fen.upper() + ' w - - 0 1'
        return fen


if __name__ == '__main__':
    Board = ShuffleBoard(True)
    for i in range(10):
        print(Board.shuffle_start())

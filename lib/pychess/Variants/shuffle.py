# Shuffle Chess

import random

from pychess.Utils.const import *
from pychess.Utils.Board import Board

class ShuffleBoard(Board):
    variant = SHUFFLECHESS

    def __init__ (self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=self.shuffle_start(), lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

    def shuffle_start(self):
        tmp = ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r']
        random.shuffle(tmp)
        tmp = ''.join(tmp)
        tmp = tmp + '/pppppppp/8/8/8/8/PPPPPPPP/' + tmp.upper() + ' w - - 0 1'
        
        return tmp

class ShuffleChess:
    __desc__ = _("xboard nocastle: http://home.hccnet.nl/h.g.muller/engine-intf.html#8\n" +
                 "FICS wild/2: http://www.freechess.org/Help/HelpFiles/wild.html\n" +
                 "* Random arrangement of the pieces behind the pawns\n" +
                 "* No castling\n" +
                 "* Black's arrangement mirrors white's")
    name = _("Shuffle")
    cecp_name = "nocastle"
    board = ShuffleBoard
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_SHUFFLE


if __name__ == '__main__':
    Board = ShuffleBoard(True)
    for i in range(10):
        print Board.shuffle_start()

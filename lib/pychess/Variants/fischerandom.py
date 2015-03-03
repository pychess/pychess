from __future__ import print_function
# Chess960 (Fischer Random Chess)

import random
from copy import copy

from pychess.Utils.const import *
from pychess.Utils.Cord import Cord
from pychess.Utils.Board import Board
from pychess.Utils.Piece import Piece
from pychess.Utils.lutils.bitboard import *
from pychess.Utils.lutils.attack import *
from pychess.Utils.lutils.lmove import FLAG, PROMOTE_PIECE


class FischerandomBoard(Board):
    variant = FISCHERRANDOMCHESS
    __desc__ = _("http://en.wikipedia.org/wiki/Chess960\n" +
                 "FICS wild/fr: http://www.freechess.org/Help/HelpFiles/wild.html")
    name = _("Fischer Random")
    cecp_name = "fischerandom"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_SHUFFLE

    
    def __init__ (self, setup=False, lboard=None):
        if setup == True:
            Board.__init__(self, setup=self.shuffle_start(), lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

    def shuffle_start(self):
        """ Create a random initial position.
            The king is placed somewhere between the two rooks.
            The bishops are placed on opposite-colored squares."""
      
        positions = [1, 2, 3, 4, 5, 6, 7, 8]
        tmp = [''] * 8
        castl = ''
        
        bishop = random.choice((1, 3, 5, 7))
        tmp[bishop-1] = 'b'
        positions.remove(bishop)

        bishop = random.choice((2, 4, 6, 8))
        tmp[bishop-1] = 'b'
        positions.remove(bishop)

        queen = random.choice(positions)
        tmp[queen-1] = 'q'
        positions.remove(queen)

        knight = random.choice(positions)
        tmp[knight-1] = 'n'
        positions.remove(knight)

        knight = random.choice(positions)
        tmp[knight-1] = 'n'
        positions.remove(knight)

        rook = positions[0]
        tmp[rook-1] = 'r'
        castl += reprFile[rook-1]

        king = positions[1]
        tmp[king-1] = 'k'

        rook = positions[2]
        tmp[rook-1] = 'r'
        castl += reprFile[rook-1]

        tmp = ''.join(tmp)
        tmp = tmp + '/pppppppp/8/8/8/8/PPPPPPPP/' + tmp.upper() + ' w ' + castl.upper() + castl +' - 0 1'
        #tmp = "rnqbbknr/pppppppp/8/8/8/8/PPPPPPPP/RNQBBKNR w AHah - 0 1"
        return tmp


if __name__ == '__main__':
    frcBoard = FischerandomBoard(True)
    for i in range(10):
        print(frcBoard.shuffle_start())

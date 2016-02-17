from __future__ import print_function
# Chess960 (Fischer Random Chess)

import random

from pychess.Utils.const import FISCHERRANDOMCHESS, VARIANTS_SHUFFLE
from pychess.Utils.Board import Board
from pychess.Utils.const import reprFile


class FischerandomBoard(Board):
    variant = FISCHERRANDOMCHESS
    __desc__ = _(
        "http://en.wikipedia.org/wiki/Chess960\n" +
        "FICS wild/fr: http://www.freechess.org/Help/HelpFiles/wild.html")
    name = _("Fischer Random")
    cecp_name = "fischerandom"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_SHUFFLE

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=self.shuffle_start(), lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

    def shuffle_start(self):
        """ Create a random initial position.
            The king is placed somewhere between the two rooks.
            The bishops are placed on opposite-colored squares."""

        positions = [1, 2, 3, 4, 5, 6, 7, 8]
        board = [''] * 8
        castl = ''

        bishop = random.choice((1, 3, 5, 7))
        board[bishop - 1] = 'b'
        positions.remove(bishop)

        bishop = random.choice((2, 4, 6, 8))
        board[bishop - 1] = 'b'
        positions.remove(bishop)

        queen = random.choice(positions)
        board[queen - 1] = 'q'
        positions.remove(queen)

        knight = random.choice(positions)
        board[knight - 1] = 'n'
        positions.remove(knight)

        knight = random.choice(positions)
        board[knight - 1] = 'n'
        positions.remove(knight)

        rook = positions[0]
        board[rook - 1] = 'r'
        castl += reprFile[rook - 1]

        king = positions[1]
        board[king - 1] = 'k'

        rook = positions[2]
        board[rook - 1] = 'r'
        castl += reprFile[rook - 1]

        fen = ''.join(board)
        fen = fen + '/pppppppp/8/8/8/8/PPPPPPPP/' + fen.upper(
        ) + ' w ' + castl.upper() + castl + ' - 0 1'
        return fen


if __name__ == '__main__':
    frcBoard = FischerandomBoard(True)
    for i in range(10):
        print(frcBoard.shuffle_start())

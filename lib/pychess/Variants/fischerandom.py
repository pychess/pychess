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


class FRCBoard(Board):
    variant = FISCHERRANDOMCHESS
    
    def __init__ (self, setup=False, lboard=None):
        if setup == True:
            Board.__init__(self, setup=self.shuffle_start(), lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

    def move (self, move, lboard=None):
        
        assert self[move.cord0], "%s %s" % (move, self.asFen())
        
        newBoard = self.clone(lboard=lboard)
        if lboard is None:
            newBoard.board.applyMove (move.move)
        
        cord0, cord1 = move.cords
        flag = FLAG(move.move)
        
        # in frc there are unusual castling positions where
        # king will move on top of the castling rook, so...
        if flag in (KING_CASTLE, QUEEN_CASTLE):
            # don't put on the castling king yet
            king = newBoard[cord0]
        else:
            newBoard[cord1] = newBoard[cord0]

        newBoard[cord0] = None
        
        # move castling rook
        if self.color == WHITE:
            if flag == QUEEN_CASTLE:
                if self.board.ini_rooks[0][0] != D1:
                    newBoard[Cord(D1)] = newBoard[Cord(self.board.ini_rooks[0][0])]
                    newBoard[Cord(self.board.ini_rooks[0][0])] = None
            elif flag == KING_CASTLE:
                if self.board.ini_rooks[0][1] != F1:
                    newBoard[Cord(F1)] = newBoard[Cord(self.board.ini_rooks[0][1])]
                    newBoard[Cord(self.board.ini_rooks[0][1])] = None
        else:
            if flag == QUEEN_CASTLE:
                if self.board.ini_rooks[1][0] != D8:
                    newBoard[Cord(D8)] = newBoard[Cord(self.board.ini_rooks[1][0])]
                    newBoard[Cord(self.board.ini_rooks[1][0])] = None
            elif flag == KING_CASTLE:
                if self.board.ini_rooks[1][1] != F8:
                    newBoard[Cord(F8)] = newBoard[Cord(self.board.ini_rooks[1][1])]
                    newBoard[Cord(self.board.ini_rooks[1][1])] = None
        
        # put the castling king now
        if flag in (KING_CASTLE, QUEEN_CASTLE):
            if self.color == WHITE:
                if flag == QUEEN_CASTLE:
                    newBoard[Cord(C1)] = king
                elif flag == KING_CASTLE:
                    newBoard[Cord(G1)] = king
            else:
                if flag == QUEEN_CASTLE:
                    newBoard[Cord(C8)] = king
                elif flag == KING_CASTLE:
                    newBoard[Cord(G8)] = king
                
        if flag in PROMOTIONS:
            newBoard[cord1] = Piece(self.color, PROMOTE_PIECE(flag))
        
        elif flag == ENPASSANT:
            newBoard[Cord(cord1.x, cord0.y)] = None
        
        return newBoard


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


class FischerRandomChess:
    __desc__ = _("http://en.wikipedia.org/wiki/Chess960\n" +
                 "FICS wild/fr: http://www.freechess.org/Help/HelpFiles/wild.html")
    name = _("Fischer Random")
    cecp_name = "fischerandom"
    board = FRCBoard
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_SHUFFLE


if __name__ == '__main__':
    frcBoard = FRCBoard(True)
    for i in range(10):
        print(frcBoard.shuffle_start())

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
        if setup is True:
            Board.__init__(self, setup=self.shuffle_start(), lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

    def simulateMove (self, board1, move):
        moved = []
        new = []
        dead = []
        
        cord0, cord1 = move.cords
        
        moved.append( (self[cord0], cord0) )
        
        if self[cord1]:
            if not move.flag in (QUEEN_CASTLE, KING_CASTLE):
                dead.append( self[cord1] )
        
        if move.flag == QUEEN_CASTLE:
            if self.color == WHITE:
                r1 = self.board.ini_rooks[0][0]
                moved.append( (self[Cord(r1)], Cord(r1)) )
            else:
                r8 = self.board.ini_rooks[1][0]
                moved.append( (self[Cord(r8)], Cord(r8)) )
        elif move.flag == KING_CASTLE:
            if self.color == WHITE:
                r1 = self.board.ini_rooks[0][1]
                moved.append( (self[Cord(r1)], Cord(r1)) )
            else:
                r8 = self.board.ini_rooks[1][1]
                moved.append( (self[Cord(r8)], Cord(r8)) )
        
        elif move.flag in PROMOTIONS:
            newPiece = board1[cord1]
            moved.append( (newPiece, cord0) )
            new.append( newPiece )
            newPiece.opacity=1
            dead.append( self[cord0] )
        
        elif move.flag == ENPASSANT:
            if self.color == WHITE:
                dead.append( self[Cord(cord1.x, cord1.y-1)] )
            else: dead.append( self[Cord(cord1.x, cord1.y+1)] )
        
        return moved, new, dead
    
    def simulateUnmove (self, board1, move):
        moved = []
        new = []
        dead = []
        
        cord0, cord1 = move.cords
        
        if not move.flag in (QUEEN_CASTLE, KING_CASTLE):
            moved.append( (self[cord1], cord1) )
        
        if board1[cord1]:
            if not move.flag in (QUEEN_CASTLE, KING_CASTLE):
                dead.append( board1[cord1] )
        
        if move.flag == QUEEN_CASTLE:
            if board1.color == WHITE:
                moved.append( (self[Cord(C1)], Cord(C1)) )
                moved.append( (self[Cord(D1)], Cord(D1)) )
            else:
                moved.append( (self[Cord(C8)], Cord(C8)) )
                moved.append( (self[Cord(D8)], Cord(D8)) )
        elif move.flag == KING_CASTLE:
            if board1.color == WHITE:
                moved.append( (self[Cord(F1)], Cord(F1)) )
                moved.append( (self[Cord(G1)], Cord(G1)) )
            else:
                moved.append( (self[Cord(F8)], Cord(F8)) )
                moved.append( (self[Cord(G8)], Cord(G8)) )
        
        elif move.flag in PROMOTIONS:
            newPiece = board1[cord0]
            moved.append( (newPiece, cord1) )
            new.append( newPiece )
            newPiece.opacity=1
            dead.append( self[cord1] )
        
        elif move.flag == ENPASSANT:
            if board1.color == WHITE:
                new.append( board1[Cord(cord1.x, cord1.y-1)] )
            else: new.append( board1[Cord(cord1.x, cord1.y+1)] )
        
        return moved, new, dead

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


def frc_castling_move(board, fcord, tcord, flag):
    if board.color == WHITE:
        if board.castling & W_OO and flag == KING_CASTLE and \
           (tcord == G1 or tcord == board.ini_rooks[WHITE][1]):
            blocker = clearBit(board.blocker, board.ini_rooks[WHITE][1])
            if fcord == B1 and not fromToRay[B1][G1] & blocker and \
                not isAttacked (board, B1, BLACK) and \
                not isAttacked (board, C1, BLACK) and \
                not isAttacked (board, D1, BLACK) and \
                not isAttacked (board, E1, BLACK) and \
                not isAttacked (board, F1, BLACK) and \
                not isAttacked (board, G1, BLACK):
                    return True

            if fcord == C1 and not fromToRay[C1][G1] & blocker and \
                not isAttacked (board, C1, BLACK) and \
                not isAttacked (board, D1, BLACK) and \
                not isAttacked (board, E1, BLACK) and \
                not isAttacked (board, F1, BLACK) and \
                not isAttacked (board, G1, BLACK):
                    return True

            if fcord == D1 and not fromToRay[D1][G1] & blocker and \
                not isAttacked (board, D1, BLACK) and \
                not isAttacked (board, E1, BLACK) and \
                not isAttacked (board, F1, BLACK) and \
                not isAttacked (board, G1, BLACK):
                    return True

            if fcord == E1 and not fromToRay[E1][G1] & blocker and \
                not isAttacked (board, E1, BLACK) and \
                not isAttacked (board, F1, BLACK) and \
                not isAttacked (board, G1, BLACK):
                    return True

            if fcord == F1 and not fromToRay[F1][G1] & blocker and \
                not isAttacked (board, F1, BLACK) and \
                not isAttacked (board, G1, BLACK):
                    return True
        
            if fcord == G1 and board.arBoard[F1] == EMPTY and \
                not isAttacked (board, G1, BLACK):
                    return True

        if board.castling & W_OOO and flag == QUEEN_CASTLE and \
           (tcord == C1 or tcord == board.ini_rooks[WHITE][0]):
            blocker = clearBit(board.blocker, board.ini_rooks[WHITE][0])
            if fcord == G1 and not fromToRay[G1][C1] & blocker and \
                not (board.ini_rooks[WHITE][0]==A1 and board.arBoard[B1] != EMPTY) and \
                not isAttacked (board, C1, BLACK) and \
                not isAttacked (board, D1, BLACK) and \
                not isAttacked (board, E1, BLACK) and \
                not isAttacked (board, F1, BLACK) and \
                not isAttacked (board, G1, BLACK):
                    return True

            if fcord == F1 and not fromToRay[F1][C1] & blocker and \
                not (board.ini_rooks[WHITE][0]==A1 and board.arBoard[B1] != EMPTY) and \
                not isAttacked (board, C1, BLACK) and \
                not isAttacked (board, D1, BLACK) and \
                not isAttacked (board, E1, BLACK) and \
                not isAttacked (board, F1, BLACK):
                    return True

            if fcord == E1 and not fromToRay[E1][C1] & blocker and \
                not (board.ini_rooks[WHITE][0]==A1 and board.arBoard[B1] != EMPTY) and \
                not isAttacked (board, C1, BLACK) and \
                not isAttacked (board, D1, BLACK) and \
                not isAttacked (board, E1, BLACK):
                    return True

            if fcord == D1 and not fromToRay[D1][C1] & blocker and \
                not (board.ini_rooks[WHITE][0]==A1 and board.arBoard[B1] != EMPTY) and \
                not isAttacked (board, C1, BLACK) and \
                not isAttacked (board, D1, BLACK):
                    return True

            if fcord == C1 and \
                board.arBoard[D1] == EMPTY and \
                not (board.ini_rooks[WHITE][0]==A1 and board.arBoard[B1] != EMPTY) and \
                not isAttacked (board, C1, BLACK):
                    return True

            if fcord == B1 and \
                board.arBoard[C1] == EMPTY and \
                board.arBoard[D1] == EMPTY and \
                not isAttacked (board, B1, BLACK) and \
                not isAttacked (board, C1, BLACK):
                    return True

    else:
        if board.castling & B_OO and flag == KING_CASTLE and \
           (tcord == G8 or tcord == board.ini_rooks[BLACK][1]):
            blocker = clearBit(board.blocker, board.ini_rooks[BLACK][1])
            if fcord == B8 and not fromToRay[B8][G8] & blocker and \
                not isAttacked (board, B8, WHITE) and \
                not isAttacked (board, C8, WHITE) and \
                not isAttacked (board, D8, WHITE) and \
                not isAttacked (board, E8, WHITE) and \
                not isAttacked (board, F8, WHITE) and \
                not isAttacked (board, G8, WHITE):
                    return True

            if fcord == C8 and not fromToRay[C8][G8] & blocker and \
                not isAttacked (board, C8, WHITE) and \
                not isAttacked (board, D8, WHITE) and \
                not isAttacked (board, E8, WHITE) and \
                not isAttacked (board, F8, WHITE) and \
                not isAttacked (board, G8, WHITE):
                    return True

            if fcord == D8 and not fromToRay[D8][G8] & blocker and \
                not isAttacked (board, D8, WHITE) and \
                not isAttacked (board, E8, WHITE) and \
                not isAttacked (board, F8, WHITE) and \
                not isAttacked (board, G8, WHITE):
                    return True

            if fcord == E8 and not fromToRay[E8][G8] & blocker and \
                not isAttacked (board, E8, WHITE) and \
                not isAttacked (board, F8, WHITE) and \
                not isAttacked (board, G8, WHITE):
                    return True

            if fcord == F8 and not fromToRay[F8][G8] & blocker and \
                not isAttacked (board, F8, WHITE) and \
                not isAttacked (board, G8, WHITE):
                    return True
        
            if fcord == G8 and board.arBoard[F8] == EMPTY and \
                not isAttacked (board, G8, WHITE):
                    return True

        if board.castling & B_OOO and flag == QUEEN_CASTLE and \
           (tcord == C8 or tcord == board.ini_rooks[BLACK][0]):
            blocker = clearBit(board.blocker, board.ini_rooks[BLACK][0])
            if fcord == G8 and not fromToRay[G8][C8] & blocker and \
                not (board.ini_rooks[BLACK][0]==A8 and board.arBoard[B8] != EMPTY) and \
                not isAttacked (board, C8, WHITE) and \
                not isAttacked (board, D8, WHITE) and \
                not isAttacked (board, E8, WHITE) and \
                not isAttacked (board, F8, WHITE) and \
                not isAttacked (board, G8, WHITE):
                    return True

            if fcord == F8 and not fromToRay[F8][C8] & blocker and \
                not (board.ini_rooks[BLACK][0]==A8 and board.arBoard[B8] != EMPTY) and \
                not isAttacked (board, C8, WHITE) and \
                not isAttacked (board, D8, WHITE) and \
                not isAttacked (board, E8, WHITE) and \
                not isAttacked (board, F8, WHITE):
                    return True

            if fcord == E8 and not fromToRay[E8][C8] & blocker and \
                not (board.ini_rooks[BLACK][0]==A8 and board.arBoard[B8] != EMPTY) and \
                not isAttacked (board, C8, WHITE) and \
                not isAttacked (board, D8, WHITE) and \
                not isAttacked (board, E8, WHITE):
                    return True

            if fcord == D8 and not fromToRay[D8][C8] & blocker and \
                not (board.ini_rooks[BLACK][0]==A8 and board.arBoard[B8] != EMPTY) and \
                not isAttacked (board, C8, WHITE) and \
                not isAttacked (board, D8, WHITE):
                    return True

            if fcord == C8 and \
                board.arBoard[D8] == EMPTY and \
                not (board.ini_rooks[BLACK][0]==A8 and board.arBoard[B8] != EMPTY) and \
                not isAttacked (board, C8, WHITE):
                    return True

            if fcord == B8 and not fromToRay[B8][C8] & blocker and \
                board.arBoard[C8] == EMPTY and \
                board.arBoard[D8] == EMPTY and \
                not isAttacked (board, B8, WHITE) and \
                not isAttacked (board, C8, WHITE):
                    return True

    return False


if __name__ == '__main__':
    frcBoard = FRCBoard(True)
    for i in range(10):
        print frcBoard.shuffle_start()

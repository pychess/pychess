# AsymmetricRandom Chess
# This is FICS wild/4 (http://www.freechess.org/Help/HelpFiles/wild.html)
# * Randomly chosen pieces (two queens or three rooks possible)
# * Exactly one king of each color
# * Pieces placed randomly behind the pawns, SUBJECT TO THE CONSTRAINT
#              THAT THE BISHOPS ARE BALANCED
# * No castling
# * Black's arrangement DOES NOT mirrors white's

import random

from pychess.Utils.const import *
from pychess.Utils.Board import Board


class AsymmetricRandomBoard(Board):
    variant = ASYMMETRICRANDOMCHESS

    def __init__ (self, setup=False):
        if setup is True:
            Board.__init__(self, setup=self.asymmetricrandom_start())
        else:
            Board.__init__(self, setup=setup)

    def asymmetricrandom_start(self):        
        white = random.sample(('r', 'n', 'b', 'q')*16, 7)
        white.append('k')        
        black = white[:]
        random.shuffle(white)
        random.shuffle(black)
        
        # balance the bishops (put them on equal numbers of dark and light squares)
        whitedarkbishops = 0
        whitelightbishops = 0
        for index, piece in enumerate(white):
            if piece == 'b':
                if index % 2 == 0:  # even numbered square on the A rank are dark
                    whitedarkbishops += 1
                else:
                    whitelightbishops += 1
        blackdarkbishops = 0
        blacklightbishops = 0
        blackbishoprandomindexstack = []
        for index, piece in enumerate(black):
            if piece == 'b':
                if index % 2 == 1:  # odd numbered squares on the H rank are dark
                    blackdarkbishops += 1
                else:
                    blacklightbishops += 1
                blackbishoprandomindexstack.append(index)
        random.shuffle(blackbishoprandomindexstack)
        class RandomEnumeratePieces:
            def __init__ (self, pieces):
                self.pieces = pieces[:]
                self.randomindexstack = range(8)
                random.shuffle(self.randomindexstack)
            def __iter__ (self):
                return self
            def next(self):
                if not self.randomindexstack:
                    raise StopIteration
                else:
                    randomindex = self.randomindexstack.pop()
                    return randomindex, self.pieces[randomindex]
        while (whitedarkbishops != blackdarkbishops) or \
              (whitelightbishops != blacklightbishops):
            bishopindex = blackbishoprandomindexstack.pop()
            for index, piece in RandomEnumeratePieces(black):
                if piece != 'b':
                    if ((blackdarkbishops > whitedarkbishops) and \
                        (bishopindex % 2 == 1) and (index % 2 == 0)):
                        black[bishopindex] = piece
                        black[index] = 'b'
                        blacklightbishops += 1
                        blackdarkbishops = blackdarkbishops > 0 and (blackdarkbishops-1) or 0
                        break
                    elif ((blacklightbishops > whitelightbishops) and \
                          (bishopindex % 2 == 0) and (index % 2 == 1)):
                        black[bishopindex] = piece
                        black[index] = 'b'
                        blackdarkbishops += 1
                        blacklightbishops = blacklightbishops > 0 and (blacklightbishops-1) or 0
                        break
                    
        tmp = ''.join(black) + '/pppppppp/8/8/8/8/PPPPPPPP/' + \
              ''.join(white).upper() + ' w - - 0 1'
        
        return tmp


class AsymmetricRandomChess:
    name = _("Asymmetric Random")
    cecp_name = "unknown"
    board = AsymmetricRandomBoard
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_SHUFFLE


if __name__ == '__main__':
    Board = AsymmetricRandomBoard(True)
    for i in range(10):
        print Board.asymmetricrandom_start()

# Wildcastle shuffle Chess

import random

from pychess.Utils.const import *
from pychess.Utils.Board import Board


class WildcastleShuffleBoard(Board):
    variant = WILDCASTLESHUFFLECHESS

    def __init__ (self, setup=False):
        if setup is True:
            Board.__init__(self, setup=self.shuffle_start())
        else:
            Board.__init__(self, setup=setup)

    # TODO: apply wild/1 rules
    def shuffle_start(self):
        tmp = ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r']
        random.shuffle(tmp)
        tmp = ''.join(tmp)
        tmp = tmp + '/pppppppp/8/8/8/8/PPPPPPPP/' + tmp.upper() + ' w KQkq - 0 1'
        
        return tmp

class WildcastleShuffleChess:
    __desc__ = _("xboard wildcastle http://home.hccnet.nl/h.g.muller/engine-intf.html#8\n"+
                 "FICS wild/1: http://www.freechess.org/Help/HelpFiles/wild.html\n"+
                 "* In this variant both sides have the same set of pieces as in normal chess.\n"+
                 "* The white king starts on d1 or e1 and the black king starts on d8 or e8,\n"+
                 "* and the rooks are in their usual positions.\n"+
                 "* Bishops are always on opposite colors.\n"+
                 "* Subject to these constraints the position of the pieces on their first ranks is random.\n"+
                 "* Castling is done similarly to normal chess:\n"+
                 "* o-o-o indicates long castling and o-o short castling.")
    name = _("Wildcastle shuffle")
    cecp_name = "wildcastle"
    board = WildcastleShuffleBoard
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_OTHER

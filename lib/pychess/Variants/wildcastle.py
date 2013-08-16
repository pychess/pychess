# Wildcastle Chess

from pychess.Utils.const import *
from pychess.Utils.Board import Board

WILDCASTLESTART = "rnbkqbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

class WildcastleBoard(Board):
    variant = WILDCASTLECHESS

    def __init__ (self, setup=False):
        if setup is True:
            Board.__init__(self, setup=WILDCASTLESTART)
        else:
            Board.__init__(self, setup=setup)


class WildcastleChess:
    __desc__ = _("xboard wildcastle http://home.hccnet.nl/h.g.muller/engine-intf.html#8\n"+
                 "FICS wild/0: http://www.freechess.org/Help/HelpFiles/wild.html\n"+
                 "* White has the typical set-up at the start.\n"+
                 "* Black's pieces are the same, except that the King and Queen are reversed,\n"+
                 "* so they are not on the same files as White's King and Queen.\n"+
                 "* Castling is done similarly to normal chess:\n"+
                 "* o-o-o indicates long castling and o-o short castling.")
    name = _("Wildcastle")
    cecp_name = "wildcastle"
    board = WildcastleBoard
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD

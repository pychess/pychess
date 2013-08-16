# Theban Chess

from pychess.Utils.const import *
from pychess.Utils.Board import Board

THEBANSTART = "1p6/2p3kn/3p2pp/4pppp/5ppp/8/PPPPPPPP/PPPPPPKN w - - 0 1"

class ThebanBoard(Board):
    variant = THEBANCHESS

    def __init__ (self, setup=False):
        if setup is True:
            Board.__init__(self, setup=THEBANSTART)
        else:
            Board.__init__(self, setup=setup)

class ThebanChess:
    __desc__ = _("Variant developed by Kai Laskos: http://talkchess.com/forum/viewtopic.php?t=40990")
    name = _("Theban")
    cecp_name = "normal"
    board = ThebanBoard
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_OTHER

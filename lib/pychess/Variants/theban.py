"""  Theban Chess Variant """

from pychess.Utils.const import THEBANCHESS, VARIANTS_OTHER
from pychess.Utils.Board import Board

THEBANSTART = "1p6/2p3kn/3p2pp/4pppp/5ppp/8/PPPPPPPP/PPPPPPKN w - - 0 1"


class ThebanBoard(Board):
    variant = THEBANCHESS
    __desc__ = _("Variant developed by Kai Laskos: http://talkchess.com/forum/viewtopic.php?t=40990")
    name = _("Theban")
    cecp_name = "normal"
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_OTHER

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=THEBANSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

"""  Upside-down Chess variant"""

from pychess.Utils.const import UPSIDEDOWNCHESS, VARIANTS_OTHER
from pychess.Utils.Board import Board

UPSIDEDOWNSTART = "RNBQKBNR/PPPPPPPP/8/8/8/8/pppppppp/rnbqkbnr w - - 0 1"


class UpsideDownBoard(Board):
    variant = UPSIDEDOWNCHESS
    __desc__ = _("FICS wild/5: http://www.freechess.org/Help/HelpFiles/wild.html\n" +
                 "http://en.wikipedia.org/wiki/Chess_variant#Chess_with_different_starting_positions\n" +
                 "Pawns start on their 7th rank rather than their 2nd rank!")
    name = _("Upside Down")
    cecp_name = "normal"
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_OTHER

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=UPSIDEDOWNSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

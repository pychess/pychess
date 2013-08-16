# Bughouse Chess

from pychess.Utils.const import *
from pychess.Utils.Board import Board

class BughouseBoard(Board):
    variant = BUGHOUSECHESS

class BughouseChess:
    __desc__ = _("FICS bughouse: http://www.freechess.org/Help/HelpFiles/bughouse.html")
    name = _("Bughouse")
    cecp_name = "bughouse"
    board = BughouseBoard
    need_initial_board = False
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD

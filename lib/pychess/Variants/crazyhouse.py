# Crazyhouse Chess

from pychess.Utils.const import *
from pychess.Utils.Board import Board

class CrazyhouseBoard(Board):
    variant = CRAZYHOUSECHESS

class CrazyhouseChess:
    __desc__ = _("FICS crazyhouse: http://www.freechess.org/Help/HelpFiles/crazyhouse.html")
    name = _("Crazyhouse")
    cecp_name = "crazyhouse"
    board = CrazyhouseBoard
    need_initial_board = False
    standard_rules = False
    variant_group = VARIANTS_OTHER

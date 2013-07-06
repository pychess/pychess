# Suicide Chess

from pychess.Utils.const import *
from pychess.Utils.Board import Board

class SuicideBoard(Board):
    variant = SUICIDECHESS

class SuicideChess:
    __desc__ = _("FICS suicide: http://www.freechess.org/Help/HelpFiles/suicide_chess.html")
    name = _("Suicide")
    cecp_name = "suicide"
    board = SuicideBoard
    need_initial_board = False
    standard_rules = False
    variant_group = VARIANTS_OTHER

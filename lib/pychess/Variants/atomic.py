# Atomic Chess

from pychess.Utils.const import *
from pychess.Utils.Board import Board

class AtomicBoard(Board):
    variant = ATOMICCHESS

class AtomicChess:
    __desc__ = _("FICS atomic: http://www.freechess.org/Help/HelpFiles/atomic.html")
    name = _("Atomic")
    cecp_name = "atomic"
    board = AtomicBoard
    need_initial_board = False
    standard_rules = False
    variant_group = VARIANTS_OTHER

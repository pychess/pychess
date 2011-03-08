# Pawns Passed Chess
# White pawns start on 5th rank and black pawns on the 4th rank

from pychess.Utils.const import *
from pychess.Utils.Board import Board

PAWNSPASSEDSTART = "rnbqkbnr/8/8/PPPPPPPP/pppppppp/8/8/RNBQKBNR w - - 0 1"


class PawnsPassedBoard(Board):
    variant = PAWNSPASSEDCHESS

    def __init__ (self, setup=False):
        if setup is True:
            Board.__init__(self, setup=PAWNSPASSEDSTART)
        else:
            Board.__init__(self, setup=setup)


class PawnsPassedChess:
    name = _("Pawns Passed")
    cecp_name = "normal"
    board = PawnsPassedBoard
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_OTHER

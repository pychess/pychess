""" Pawns Passed Chess """

from pychess.Utils.const import PAWNSPASSEDCHESS, VARIANTS_OTHER
from pychess.Utils.Board import Board

PAWNSPASSEDSTART = "rnbqkbnr/8/8/PPPPPPPP/pppppppp/8/8/RNBQKBNR w - - 0 1"


class PawnsPassedBoard(Board):
    """:Description: Standard chess game rules, but where the board setup is defined as all the
        white pawns start on the 5th rank and all the black pawns start on the 4th rank
    """
    variant = PAWNSPASSEDCHESS
    __desc__ = _("FICS wild/8a: http://www.freechess.org/Help/HelpFiles/wild.html\n" +
                 "White pawns start on 5th rank and black pawns on the 4th rank")
    name = _("Pawns Passed")
    cecp_name = "normal"
    need_initial_board = True
    standard_rules = True
    variant_group = VARIANTS_OTHER

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=PAWNSPASSEDSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

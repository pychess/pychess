from pychess.Utils.const import PLACEMENTCHESS, VARIANTS_OTHER_NONSTANDARD
from pychess.Utils.Board import Board


# Placement chess (Bronstein/Benko/Pre-chess)
# http://www.quantumgambitz.com/blog/chess/cga/bronstein-chess-pre-chess-shuffle-chess
PLACEMENTSTART = "8/pppppppp/8/8/8/8/PPPPPPPP/8/nnbbrrqkNNBBRRQK w - - 0 1"


class PlacementBoard(Board):
    variant = PLACEMENTCHESS
    __desc__ = _("Pre-chess: https://en.wikipedia.org/wiki/List_of_chess_variants#Different_starting_position")
    name = _("Placement")
    cecp_name = "placement"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=PLACEMENTSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

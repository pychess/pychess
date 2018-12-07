""" Three-check Chess Variant """

from pychess.Utils.const import THREECHECKCHESS, VARIANTS_OTHER_NONSTANDARD
from pychess.Utils.Board import Board

THREECHECKSTART = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 3+3 0 1"


class ThreeCheckBoard(Board):
    variant = THREECHECKCHESS
    __desc__ = _("Win by giving check 3 times")
    name = _("Three-check")
    cecp_name = "3check"
    need_initial_board = False
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=THREECHECKSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)


def checkCount(board, color):
    lboard = board.clone()
    if color != board.color and lboard.hist_move:
        lboard.popMove()
    cc = 3 - board.remaining_checks[board.color]
    while lboard.hist_move:
        if lboard.isChecked():
            cc += 1
        lboard.popMove()
        if lboard.hist_move:
            lboard.popMove()
    return cc

""" Three-check Chess Variant """
from __future__ import absolute_import
from __future__ import print_function

from pychess.Utils.const import THREECHECKCHESS, VARIANTS_OTHER_NONSTANDARD
from pychess.Utils.Board import Board


class ThreeCheckBoard(Board):
    variant = THREECHECKCHESS
    __desc__ = _("Win by giving check 3 times")
    name = _("Three-check")
    cecp_name = "3check"
    need_initial_board = False
    standard_rules = False
    variant_group = VARIANTS_OTHER_NONSTANDARD


def checkCount(board):
    cc = 0
    lboard = board.clone()
    while lboard.hist_move:
        if lboard.isChecked():
            cc += 1
        lboard.popMove()
        if lboard.hist_move:
            lboard.popMove()
    return cc

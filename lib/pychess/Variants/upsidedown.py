# Upside-down Chess
# http://en.wikipedia.org/wiki/Chess_variant#Chess_with_different_starting_positions

import random

# used only for selftesting
#import __builtin__
#__builtin__.__dict__['_'] = lambda s: s

from pychess.Utils.const import *
from pychess.Utils.Board import Board

UPSIDEDOWNSTART = "RNBQKBNR/PPPPPPPP/8/8/8/8/pppppppp/rnbqkbnr w - - 0 1"


class UpsideDownBoard(Board):

    variant = UPSIDEDOWNCHESS

    def __init__ (self, setup=False):
        if setup is True:
            Board.__init__(self, setup=UPSIDEDOWNSTART)
        else:
            Board.__init__(self, setup=setup)


class UpsideDownChess:
    name = _("Upside-down")
    cecp_name = "normal"
    board = UpsideDownBoard
    need_initial_board = True
    standard_rules = True


# Losers Chess
# http://www.freechess.org/Help/HelpFiles/losers_chess.html

import random

# used only for selftesting
#import __builtin__
#__builtin__.__dict__['_'] = lambda s: s

from pychess.Utils.const import *
from pychess.Utils.Board import Board


class LosersBoard(Board):

    variant = LOSERSCHESS


class LosersChess:
    name = _("Losers")
    cecp_name = "losers"
    board = LosersBoard
    need_initial_board = False
    standard_rules = False


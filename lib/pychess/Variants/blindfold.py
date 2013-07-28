from pychess.Utils.const import *
from pychess.Utils.Board import Board


class BlindfoldBoard(Board):
    variant = BLINDFOLDCHESS


class BlindfoldChess:
    __desc__ = _("Classic chess rules with hidden figurines\n" +
                 "http://en.wikipedia.org/wiki/Blindfold_chess")
    name = _("Blindfold")
    cecp_name = "normal"
    board = BlindfoldBoard
    need_initial_board = False
    standard_rules = True
    variant_group = VARIANTS_BLINDFOLD


class HiddenPawnsBoard(Board):
    variant = HIDDENPAWNSCHESS


class HiddenPawnsChess:
    __desc__ = _("Classic chess rules with hidden pawns\n" +
                 "http://en.wikipedia.org/wiki/Blindfold_chess")
    name = _("Hidden pawns")
    cecp_name = "normal"
    board = HiddenPawnsBoard
    need_initial_board = False
    standard_rules = True
    variant_group = VARIANTS_BLINDFOLD


class HiddenPiecesBoard(Board):
    variant = HIDDENPIECESCHESS


class HiddenPiecesChess:
    __desc__ = _("Classic chess rules with hidden pieces\n" +
                 "http://en.wikipedia.org/wiki/Blindfold_chess")
    name = _("Hidden pieces")
    cecp_name = "normal"
    board = HiddenPiecesBoard
    need_initial_board = False
    standard_rules = True
    variant_group = VARIANTS_BLINDFOLD


class AllWhiteBoard(Board):
    variant = ALLWHITECHESS


class AllWhiteChess:
    __desc__ = _("Classic chess rules with all pieces white\n" +
                 "http://en.wikipedia.org/wiki/Blindfold_chess")
    name = _("All white")
    cecp_name = "normal"
    board = AllWhiteBoard
    need_initial_board = False
    standard_rules = True
    variant_group = VARIANTS_BLINDFOLD

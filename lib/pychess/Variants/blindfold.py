from pychess.Utils.const import (
    VARIANTS_BLINDFOLD,
    BLINDFOLDCHESS,
    HIDDENPAWNSCHESS,
    HIDDENPIECESCHESS,
    ALLWHITECHESS,
    ALLPAWNSCHESS,
    ALLWHITEPAWNSCHESS,
    HIDDENWHITECHESS,
    HIDDENBLACKCHESS,
)
from pychess.Utils.Board import Board


class BlindfoldBoard(Board):
    variant = BLINDFOLDCHESS
    __desc__ = _(
        "Classic chess rules with hidden figurines\n"
        + "http://en.wikipedia.org/wiki/Blindfold_chess"
    )
    name = _("Blindfold")
    cecp_name = "normal"
    need_initial_board = False
    standard_rules = True
    variant_group = VARIANTS_BLINDFOLD


class HiddenPawnsBoard(Board):
    variant = HIDDENPAWNSCHESS
    __desc__ = _(
        "Classic chess rules with hidden pawns\n"
        + "http://en.wikipedia.org/wiki/Blindfold_chess"
    )
    name = _("Hidden pawns")
    cecp_name = "normal"
    need_initial_board = False
    standard_rules = True
    variant_group = VARIANTS_BLINDFOLD


class HiddenPiecesBoard(Board):
    variant = HIDDENPIECESCHESS
    __desc__ = _(
        "Classic chess rules with hidden pieces\n"
        + "http://en.wikipedia.org/wiki/Blindfold_chess"
    )
    name = _("Hidden pieces")
    cecp_name = "normal"
    need_initial_board = False
    standard_rules = True
    variant_group = VARIANTS_BLINDFOLD


class AllWhiteBoard(Board):
    variant = ALLWHITECHESS
    __desc__ = _(
        "Classic chess rules with all pieces white\n"
        + "http://en.wikipedia.org/wiki/Blindfold_chess"
    )
    name = _("All white")
    cecp_name = "normal"
    need_initial_board = False
    standard_rules = True
    variant_group = VARIANTS_BLINDFOLD


class AllPawnsBoard(Board):
    variant = ALLPAWNSCHESS
    __desc__ = _(
        "Classic chess rules with all pieces pawns\n"
        + "http://en.wikipedia.org/wiki/Blindfold_chess"
    )
    name = _("All pawns")
    cecp_name = "normal"
    need_initial_board = False
    standard_rules = True
    variant_group = VARIANTS_BLINDFOLD


class AllWhitePawnsBoard(Board):
    variant = ALLWHITEPAWNSCHESS
    __desc__ = _(
        "Classic chess rules with all pieces white pawns\n"
        + "http://en.wikipedia.org/wiki/Blindfold_chess"
    )
    name = _("All white pawns")
    cecp_name = "normal"
    need_initial_board = False
    standard_rules = True
    variant_group = VARIANTS_BLINDFOLD


class HiddenWhiteBoard(Board):
    variant = HIDDENWHITECHESS
    __desc__ = _(
        "Classic chess rules with white figurines hidden\n"
        + "http://en.wikipedia.org/wiki/Blindfold_chess"
    )
    name = _("Hidden white")
    cecp_name = "normal"
    need_initial_board = False
    standard_rules = True
    variant_group = VARIANTS_BLINDFOLD


class HiddenBlackBoard(Board):
    variant = HIDDENBLACKCHESS
    __desc__ = _(
        "Classic chess rules with black figurines hidden\n"
        + "http://en.wikipedia.org/wiki/Blindfold_chess"
    )
    name = _("Hidden black")
    cecp_name = "normal"
    need_initial_board = False
    standard_rules = True
    variant_group = VARIANTS_BLINDFOLD

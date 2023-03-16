#############
# ASEAN-Chess
#############

from pychess.Utils.const import (
    VARIANTS_ASEAN,
    ASEANCHESS,
    MAKRUKCHESS,
    QUEEN_PROMOTION,
    CAMBODIANCHESS,
    AIWOKCHESS,
    SITTUYINCHESS,
    NORMAL_MOVE,
    A1,
    A3,
    A6,
    A8,
    B2,
    B3,
    B6,
    B7,
    C3,
    C6,
    D3,
    D4,
    D5,
    D6,
    E3,
    E4,
    E5,
    E6,
    F3,
    F6,
    G2,
    G3,
    G6,
    G7,
    H1,
    H3,
    H6,
    H8,
)

from pychess.Utils.Board import Board

ASEANSTART = "rnbqkbnr/8/pppppppp/8/8/PPPPPPPP/8/RNBQKBNR w - - 0 1"


class AseanBoard(Board):
    variant = ASEANCHESS
    __desc__ = _(
        "ASEAN: http://www.ncf-phil.org/downloadables/2014/May/Asean_chess/Laws_of_ASEAN_Chess_2011_Nov_26.doc"
    )
    name = _("ASEAN")
    cecp_name = "asean"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_ASEAN

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=ASEANSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)


#######################
# Makruk, or Thai chess
#######################
MAKRUKSTART = "rnsmksnr/8/pppppppp/8/8/PPPPPPPP/8/RNSKMSNR w - - 0 1"


class MakrukBoard(Board):
    variant = MAKRUKCHESS
    __desc__ = _("Makruk: http://en.wikipedia.org/wiki/Makruk")
    name = _("Makruk")
    cecp_name = "makruk"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_ASEAN

    PROMOTION_ZONE = (
        (A6, B6, C6, D6, E6, F6, G6, H6),
        (A3, B3, C3, D3, E3, F3, G3, H3),
    )
    PROMOTIONS = (QUEEN_PROMOTION,)

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=MAKRUKSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)


##################################
# Ouk Chatrang, or Cambodian Makruk
##################################
# DEde in cambodian starting fen indicate
# that queens and kings are virgins (not moved yet)
KAMBODIANSTART = "rnsmksnr/8/pppppppp/8/8/PPPPPPPP/8/RNSKMSNR w DEde - 0 1"


class CambodianBoard(Board):
    variant = CAMBODIANCHESS
    __desc__ = _("Cambodian: http://www.khmerinstitute.org/culture/ok.html")
    name = _("Cambodian")
    cecp_name = "cambodian"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_ASEAN

    PROMOTION_ZONE = (
        (A6, B6, C6, D6, E6, F6, G6, H6),
        (A3, B3, C3, D3, E3, F3, G3, H3),
    )
    PROMOTIONS = (QUEEN_PROMOTION,)

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=KAMBODIANSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)


###############
# Ai-Wok Makruk
###############

AIWOKSTART = "rnsaksnr/8/pppppppp/8/8/PPPPPPPP/8/RNSKASNR w - - 0 1"


class AiWokBoard(Board):
    variant = AIWOKCHESS
    __desc__ = _(
        "Ai-Wok: http://www.open-aurec.com/wbforum/viewtopic.php?p=199364&sid=20963a1de2c164050de019e5ed6bf7c4#p199364"
    )
    name = _("Ai-Wok")
    cecp_name = "ai-wok"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_ASEAN

    PROMOTION_ZONE = (
        (A6, B6, C6, D6, E6, F6, G6, H6),
        (A3, B3, C3, D3, E3, F3, G3, H3),
    )
    PROMOTIONS = (QUEEN_PROMOTION,)

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=AIWOKSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)


############################
# Sittuyin, or Myanmar Chess
############################
# Official rules:
# https://vdocuments.net/how-to-play-myanmar-traditional-chess-eng-book-1.html

SITTUYINSTART = "8/8/4pppp/pppp4/4PPPP/PPPP4/8/8/rrnnssfkRRNNSSFK w - - 0 1"


class SittuyinBoard(Board):
    variant = SITTUYINCHESS
    __desc__ = _("Sittuyin: http://en.wikipedia.org/wiki/Sittuyin")
    name = _("Sittuyin")
    cecp_name = "sittuyin"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_ASEAN

    PROMOTION_ZONE = (
        (A8, B7, C6, D5, E5, F6, G7, H8),
        (A1, B2, C3, D4, E4, F3, G2, H1),
    )
    PROMOTIONS = (QUEEN_PROMOTION, NORMAL_MOVE)

    def __init__(self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=SITTUYINSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

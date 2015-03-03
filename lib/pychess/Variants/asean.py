#############
# ASEAN-Chess
#############

from pychess.Utils.const import *
from pychess.Utils.Board import Board

ASEANSTART = "rnbqkbnr/8/pppppppp/8/8/PPPPPPPP/8/RNBQKBNR w - - 0 1"

class AseanBoard(Board):
    variant = ASEANCHESS
    __desc__ = _("ASEAN: http://www.ncf-phil.org/downloadables/2014/May/Asean_chess/Laws_of_ASEAN_Chess_2011_Nov_26.doc")
    name = _("ASEAN")
    cecp_name = "asean"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_ASEAN

    def __init__ (self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=ASEANSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)


#######################
# Makruk, or Thai chess
#######################
MAKRUKSTART = "rnbkqbnr/8/pppppppp/8/8/PPPPPPPP/8/RNBQKBNR w - - 0 1"

class MakrukBoard(Board):
    variant = MAKRUKCHESS
    __desc__ = _("Makruk: http://en.wikipedia.org/wiki/Makruk")
    name = _("Makruk")
    cecp_name = "makruk"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_ASEAN

    PROMOTION_ZONE = ((A6, B6, C6, D6, E6, F6, G6, H6), \
                      (A3, B3, C3, D3, E3, F3, G3, H3))
    PROMOTIONS = (QUEEN_PROMOTION,)

    def __init__ (self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=MAKRUKSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)


##################################
# Ouk Chatrang, or Cambodian Makruk
##################################

class KambodianBoard(Board):
    variant = KAMBODIANCHESS
    __desc__ = _("Kambodian: http://history.chess.free.fr/cambodian.htm")
    name = _("Kambodian")
    cecp_name = "kambodian"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_ASEAN

    PROMOTION_ZONE = ((A6, B6, C6, D6, E6, F6, G6, H6), \
                      (A3, B3, C3, D3, E3, F3, G3, H3))
    PROMOTIONS = (QUEEN_PROMOTION,)

    def __init__ (self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=MAKRUKSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)


###############
# Ai-Wok Makruk
###############

class AiWokBoard(Board):
    variant = AIWOKCHESS
    __desc__ = _("Ai-Wok: http://www.open-aurec.com/wbforum/viewtopic.php?p=199364&sid=20963a1de2c164050de019e5ed6bf7c4#p199364")
    name = _("Ai-Wok")
    cecp_name = "ai-wok"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_ASEAN

    PROMOTION_ZONE = ((A6, B6, C6, D6, E6, F6, G6, H6), \
                      (A3, B3, C3, D3, E3, F3, G3, H3))
    PROMOTIONS = (QUEEN_PROMOTION,)

    def __init__ (self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=MAKRUKSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)


############################
# Sittuyin, or Myanmar Chess
############################
SITTUYINSTART = "8/8/4pppp/pppp4/PPPP4/4PPPP/8/8/rrnnbbqkRRNNBBQK w - - 0 1"

class SittuyinBoard(Board):
    variant = SITTUYINCHESS
    __desc__ = _("Sittuyin: http://en.wikipedia.org/wiki/Sittuyin")
    name = _("Sittuyin")
    cecp_name = "sittuyin"
    need_initial_board = True
    standard_rules = False
    variant_group = VARIANTS_ASEAN

    PROMOTION_ZONE = ((A6, B6, C6, D6, E6, F6, G6, H6), \
                      (A3, B3, C3, D3, E3, F3, G3, H3))
    PROMOTIONS = (QUEEN_PROMOTION,)

    def __init__ (self, setup=False, lboard=None):
        if setup is True:
            Board.__init__(self, setup=SITTUYINSTART, lboard=lboard)
        else:
            Board.__init__(self, setup=setup, lboard=lboard)

from pychess import Variants
from pychess.Utils.const import *

# RatingType
TYPE_BLITZ, TYPE_STANDARD, TYPE_LIGHTNING, TYPE_WILD, \
    TYPE_BUGHOUSE, TYPE_CRAZYHOUSE, TYPE_SUICIDE, TYPE_LOSERS, TYPE_ATOMIC, \
    TYPE_UNTIMED, TYPE_EXAMINED, TYPE_OTHER = range(12)

class GameType (object):
    def __init__ (self, fics_name, short_fics_name, rating_type,
                  display_text=None, variant_type=NORMALCHESS):
        self.fics_name = fics_name
        self.short_fics_name = short_fics_name
        self.rating_type = rating_type
        if display_text:
            self.display_text=display_text
        self.variant_type = variant_type
    @property
    def variant (self):
        return Variants.variants[self.variant_type]
    def __repr__ (self):
        s = "<GameType "
        s += "fics_name='%s', " % self.fics_name
        s += "short_fics_name='%s', " % self.short_fics_name
        s += "rating_type=%d, " % self.rating_type
        s += "variant_type=%d, " % self.variant_type
        s += "display_text='%s'>" % self.display_text
        return s
    
class NormalGameType (GameType):
    def __init__ (self, fics_name, short_fics_name, rating_type, display_text):
        GameType.__init__(self, fics_name, short_fics_name, rating_type,
                          display_text=display_text)
        
class VariantGameType (GameType):
    def __init__ (self, fics_name, short_fics_name, rating_type, variant_type):
        GameType.__init__(self, fics_name, short_fics_name, rating_type,
                          variant_type=variant_type)
    @property
    def display_text (self):
        assert self.variant_type != None
        return Variants.variants[self.variant_type].name
    @property
    def seek_text (self):
        return self.fics_name.replace("/", " ")

class WildGameType (VariantGameType):
    _instances = []
    def __init__ (self, fics_name, variant_type):
        VariantGameType.__init__(self, fics_name, "w", TYPE_WILD,
                                 variant_type=variant_type)
        WildGameType._instances.append(self)
    @classmethod
    def instances (cls):
        return cls._instances

GAME_TYPES = {
    "blitz": NormalGameType("blitz", "b", TYPE_BLITZ, _("Blitz")),
    "standard": NormalGameType("standard", "s", TYPE_STANDARD, _("Standard")),
    "lightning": NormalGameType("lightning", "l", TYPE_LIGHTNING, _("Lightning")),
    "untimed": NormalGameType("untimed", "u", TYPE_UNTIMED, _("Untimed")),
    "examined": NormalGameType("examined", "e", TYPE_EXAMINED, _("Examined")),    
    "nonstandard": NormalGameType("nonstandard", "n", TYPE_OTHER, _("Other")),    
    "losers": VariantGameType("losers", "L", TYPE_LOSERS, LOSERSCHESS),
    "wild/fr": WildGameType("wild/fr", FISCHERRANDOMCHESS),
    "wild/2": WildGameType("wild/2", SHUFFLECHESS),
    "wild/3": WildGameType("wild/3", RANDOMCHESS),
    "wild/4": WildGameType("wild/4", ASYMMETRICRANDOMCHESS),
    "wild/5": WildGameType("wild/5", UPSIDEDOWNCHESS),
    "wild/8": WildGameType("wild/8", PAWNSPUSHEDCHESS),
    "wild/8a": WildGameType("wild/8a", PAWNSPASSEDCHESS)
}
# unsupported:
#    "bughouse": VariantGameType("bughouse", "B", TYPE_BUGHOUSE, BUGHOUSECHESS),
#    "crazyhouse": VariantGameType("crazyhouse", "z", TYPE_CRAZYHOUSE, CRAZYHOUSECHESS),
#    "suicide": VariantGameType("suicide", "S", TYPE_SUICIDE, SUICIDECHESS),
#    "atomic": VariantGameType("atomic", "x", TYPE_ATOMIC, ATOMICCHESS),

VARIANT_GAME_TYPES = {}
for key in GAME_TYPES:
    if isinstance(GAME_TYPES[key], VariantGameType):
        VARIANT_GAME_TYPES[GAME_TYPES[key].variant_type] = GAME_TYPES[key]

# The following 3 GAME_TYPES_* data structures don't have any real entries
# for the WildGameType's in GAME_TYPES above, and instead use
# a dummy type for the all-encompassing "Wild" FICS rating for wild/* games
GAME_TYPES_BY_SHORT_FICS_NAME = {
    "w": GameType("wild", "w", TYPE_WILD, display_text=_("Wild"))
}
for key in GAME_TYPES:
    if not isinstance(GAME_TYPES[key], WildGameType):
        GAME_TYPES_BY_SHORT_FICS_NAME[GAME_TYPES[key].short_fics_name] = \
            GAME_TYPES[key]

GAME_TYPES_BY_RATING_TYPE = {}
for key in GAME_TYPES_BY_SHORT_FICS_NAME:
    GAME_TYPES_BY_RATING_TYPE[GAME_TYPES_BY_SHORT_FICS_NAME[key].rating_type] = \
         GAME_TYPES_BY_SHORT_FICS_NAME[key]

GAME_TYPES_BY_FICS_NAME = {}
for key in GAME_TYPES_BY_SHORT_FICS_NAME:
    GAME_TYPES_BY_FICS_NAME[GAME_TYPES_BY_SHORT_FICS_NAME[key].fics_name] = \
         GAME_TYPES_BY_SHORT_FICS_NAME[key]

def type_to_display_text (typename):
    if "loaded from" in typename.lower():
        typename = typename.split()[-1]
    if typename in GAME_TYPES:
        return GAME_TYPES[typename].display_text
    # Default solution for eco/A00 and a few others
    elif "/" in typename:
        a, b = typename.split("/")
        a = a[0].upper() + a[1:]
        b = b[0].upper() + b[1:]
        return a + " " + b
    else:
        # Otherwise forget about it
        return typename[0].upper() + typename[1:]

def time_control_to_gametype (minutes, gain):
    assert type(minutes) == int and type(gain) == int
    assert minutes >= 0 and gain >= 0
    gainminutes = gain > 0 and (gain*60)-1 or 0
    if minutes is 0:
        return GAME_TYPES["untimed"]
    elif (minutes*60) + gainminutes >= (15*60):
        return GAME_TYPES["standard"]
    elif (minutes*60) + gainminutes >= (3*60):
        return GAME_TYPES["blitz"]
    else:
        return GAME_TYPES["lightning"]

TYPE_ADMINISTRATOR, TYPE_BLINDFOLD, TYPE_COMPUTER, \
    TYPE_TEAM, TYPE_UNREGISTERED, TYPE_CHESS_ADVISOR, \
    TYPE_SERVICE_REPRESENTATIVE, TYPE_TOURNAMENT_DIRECTOR, TYPE_MAMER_MANAGER, \
    TYPE_GRAND_MASTER, TYPE_INTERNATIONAL_MASTER, TYPE_FIDE_MASTER, \
    TYPE_WOMAN_GRAND_MASTER, TYPE_WOMAN_INTERNATIONAL_MASTER, \
    TYPE_DUMMY_ACCOUNT = range(15)

TITLE_TYPE_DISPLAY_TEXTS = (
    _("Administrator"), _("Blindfold Account"), _("Computer Account"),
    _("Team Account"), _("Unregistered User"), _("Chess Advisor"),
    _("Service Representative"), _("Tournament Director"), _("Mamer Manager"),
    _("Grand Master"), _("International Master"), _("FIDE Master"),
    _("Woman Grand Master"), _("Woman International Master"), _("Dummy Account"),
)

TITLE_TYPE_DISPLAY_TEXTS_SHORT = (
    _("*"), _("B"), _("C"),
    _("T"), _("U"), _("CA"),
    _("SR"), _("TD"), _("TM"),
    _("GM"), _("IM"), _("FM"),
    _("WGM"), _("WIM"), _("D")
)

TITLES = {  # From FICS 'help who'
    "*": TYPE_ADMINISTRATOR,
    "B": TYPE_BLINDFOLD,
    "C": TYPE_COMPUTER,
    "T": TYPE_TEAM,
    "U": TYPE_UNREGISTERED,
    "CA": TYPE_CHESS_ADVISOR,
    "SR": TYPE_SERVICE_REPRESENTATIVE,
    "TD": TYPE_TOURNAMENT_DIRECTOR,
    "TM": TYPE_MAMER_MANAGER,
    "GM": TYPE_GRAND_MASTER,
    "IM": TYPE_INTERNATIONAL_MASTER,
    "FM": TYPE_FIDE_MASTER,
    "WIM": TYPE_WOMAN_INTERNATIONAL_MASTER,
    "WGM": TYPE_WOMAN_GRAND_MASTER,
    "D":   TYPE_DUMMY_ACCOUNT,
}

HEX_TO_TITLE = {
    0x1 : TYPE_UNREGISTERED,
    0x2 : TYPE_COMPUTER,
    0x4 : TYPE_GRAND_MASTER,
    0x8 : TYPE_INTERNATIONAL_MASTER,
    0x10 : TYPE_FIDE_MASTER,
    0x20 : TYPE_WOMAN_GRAND_MASTER,
    0x40 : TYPE_WOMAN_INTERNATIONAL_MASTER,
    0x80 : TYPE_FIDE_MASTER,
}

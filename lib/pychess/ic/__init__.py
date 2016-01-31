import re

from gi.repository import Gtk

from pychess import Variants
from pychess.Utils.const import *


IC_CONNECTED, IC_DISCONNECTED = range(2)

IC_POS_ISOLATED, IC_POS_OBSERVING_EXAMINATION, IC_POS_EXAMINATING, \
IC_POS_OP_TO_MOVE, IC_POS_ME_TO_MOVE, IC_POS_OBSERVING, IC_POS_INITIAL = range(7)

# RatingType
TYPE_BLITZ, TYPE_STANDARD, TYPE_LIGHTNING, TYPE_WILD, \
TYPE_BUGHOUSE, TYPE_CRAZYHOUSE, TYPE_SUICIDE, TYPE_LOSERS, TYPE_ATOMIC, \
TYPE_UNTIMED, TYPE_EXAMINED, TYPE_OTHER = range(12)

RATING_TYPES = (
    TYPE_BLITZ, TYPE_STANDARD, TYPE_LIGHTNING, TYPE_ATOMIC, TYPE_BUGHOUSE,
    TYPE_CRAZYHOUSE, TYPE_LOSERS, TYPE_SUICIDE, TYPE_WILD,
)

# Rating deviations
DEVIATION_NONE, DEVIATION_ESTIMATED, DEVIATION_PROVISIONAL = range(3)

IC_STATUS_PLAYING, IC_STATUS_ACTIVE, IC_STATUS_BUSY, IC_STATUS_OFFLINE, \
IC_STATUS_AVAILABLE, IC_STATUS_NOT_AVAILABLE, IC_STATUS_EXAMINING, \
IC_STATUS_IDLE, IC_STATUS_IN_TOURNAMENT, IC_STATUS_RUNNING_SIMUL_MATCH, \
IC_STATUS_UNKNOWN = range(11)

TITLES_RE = "(?:\([A-Z*]+\))*"
NAMES_RE = "[A-Za-z]+"

DEVIATION = {
    "E": DEVIATION_ESTIMATED,
    "P": DEVIATION_PROVISIONAL,
    " ": DEVIATION_NONE,
    "" : DEVIATION_NONE,
}

STATUS = {
    "^": IC_STATUS_PLAYING,
    " ": IC_STATUS_AVAILABLE,
    ".": IC_STATUS_IDLE,
    "#": IC_STATUS_EXAMINING,
    ":": IC_STATUS_NOT_AVAILABLE,
    "~": IC_STATUS_RUNNING_SIMUL_MATCH,
    "&": IC_STATUS_IN_TOURNAMENT,
}

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
    "atomic": VariantGameType("atomic", "x", TYPE_ATOMIC, ATOMICCHESS),
    "bughouse": VariantGameType("bughouse", "B", TYPE_BUGHOUSE, BUGHOUSECHESS),
    "crazyhouse": VariantGameType("crazyhouse", "z", TYPE_CRAZYHOUSE, CRAZYHOUSECHESS),
    "losers": VariantGameType("losers", "L", TYPE_LOSERS, LOSERSCHESS),
    "suicide": VariantGameType("suicide", "S", TYPE_SUICIDE, SUICIDECHESS),
    "wild/fr": WildGameType("wild/fr", FISCHERRANDOMCHESS),
    "wild/0": WildGameType("wild/0", WILDCASTLECHESS),
    "wild/1": WildGameType("wild/1", WILDCASTLESHUFFLECHESS),
    "wild/2": WildGameType("wild/2", SHUFFLECHESS),
    "wild/3": WildGameType("wild/3", RANDOMCHESS),
    "wild/4": WildGameType("wild/4", ASYMMETRICRANDOMCHESS),
    "wild/5": WildGameType("wild/5", UPSIDEDOWNCHESS),
    "wild/8": WildGameType("wild/8", PAWNSPUSHEDCHESS),
    "wild/8a": WildGameType("wild/8a", PAWNSPASSEDCHESS)
}

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
    assert isinstance(minutes, int) and isinstance(gain, int)
    assert minutes >= 0 and gain >= 0
    gainminutes = gain > 0 and (gain*60)-1 or 0
    if minutes == 0 and gain == 0:
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
    TYPE_WOMAN_GRAND_MASTER, TYPE_WOMAN_INTERNATIONAL_MASTER, TYPE_WOMAN_FIDE_MASTER,\
    TYPE_DUMMY_ACCOUNT, TYPE_CANDIDATE_MASTER, TYPE_FIDE_ARBEITER, TYPE_NATIONAL_MASTER = range(19)

TITLE_TYPE_DISPLAY_TEXTS = (
    _("Administrator"), _("Blindfold Account"), _("Computer"),
    _("Team Account"), _("Unregistered"), _("Chess Advisor"),
    _("Service Representative"), _("Tournament Director"), _("Mamer Manager"),
    _("Grand Master"), _("International Master"), _("FIDE Master"),
    _("Woman Grand Master"), _("Woman International Master"), _("Woman FIDE Master"),
    _("Dummy Account"),
)

TITLE_TYPE_DISPLAY_TEXTS_SHORT = (
    _("*"), _("B"), _("C"),
    _("T"), _("U"), _("CA"),
    _("SR"), _("TD"), _("TM"),
    _("GM"), _("IM"), _("FM"),
    _("WGM"), _("WIM"), _("WFM"), _("D"), _("H"), _("CM"), _("FA"), _("NM")
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
    "WFM": TYPE_WOMAN_FIDE_MASTER,
    "WIM": TYPE_WOMAN_INTERNATIONAL_MASTER,
    "WGM": TYPE_WOMAN_GRAND_MASTER,
    "D":   TYPE_DUMMY_ACCOUNT,
    "H": TYPE_SERVICE_REPRESENTATIVE,
    "CM": TYPE_CANDIDATE_MASTER,
    "FA": TYPE_FIDE_ARBEITER,
    "NM": TYPE_NATIONAL_MASTER,
}

HEX_TO_TITLE = {
    0x1 : TYPE_UNREGISTERED,
    0x2 : TYPE_COMPUTER,
    0x4 : TYPE_GRAND_MASTER,
    0x8 : TYPE_INTERNATIONAL_MASTER,
    0x10 : TYPE_FIDE_MASTER,
    0x20 : TYPE_WOMAN_GRAND_MASTER,
    0x40 : TYPE_WOMAN_INTERNATIONAL_MASTER,
    0x80 : TYPE_WOMAN_FIDE_MASTER,
}

def parse_title_hex (titlehex):
    titles = set()
    for key in HEX_TO_TITLE:
        if int(titlehex, 16) & key:
            titles.add(HEX_TO_TITLE[key])
    return titles

def get_infobarmessage_content (player, text, gametype=None):
    content = Gtk.HBox()
    icon = Gtk.Image()
    icon.set_from_pixbuf(player.getIcon(size=32, gametype=gametype))
    content.pack_start(icon, False, False, 4)
    label = Gtk.Label()
    label.set_markup(player.getMarkup(gametype=gametype))
    content.pack_start(label, False, False, 0)
    label = Gtk.Label()
    label.set_markup(text)
    content.pack_start(label, False, False, 0)
    return content

def get_infobarmessage_content2 (player, heading_text, message_text,
                                 gametype=None):
    hbox = Gtk.HBox()
    image = Gtk.Image()
    image.set_from_pixbuf(player.getIcon(size=24, gametype=gametype))
    hbox.pack_start(image, False, False, 0)
    label = Gtk.Label()
    markup = player.getMarkup(gametype=gametype, long_titles=False)
    label.set_markup(markup + heading_text)
    hbox.pack_start(label, False, False, 0)
    vbox = Gtk.VBox()
    vbox.pack_start(hbox, False, False, 0)
    label = Gtk.Label()
    label.props.xalign = 0
    label.props.xpad = 4
    label.props.justify = Gtk.Justification.LEFT
    label.props.wrap = True
    label.set_width_chars(70)
    label.set_text(message_text)
    vbox.pack_start(label, False, False, 5)
    return vbox
    
"""
Internal command codes used in FICS block mode
(see "help block_codes" and "help iv_block").
Used mostly by internal library functions.

BLOCK_ variables are message boundary markers.

BLKCMD_ variables are command codes.
"""

BLOCK_START = chr(21)        # \U
BLOCK_SEPARATOR = chr(22)    # \V
BLOCK_END = chr(23)          # \W
BLOCK_POSE_START = chr(24)   # \X
BLOCK_POSE_END = chr(25)     # \Y

BLKCMD_NULL = 0
BLKCMD_GAME_MOVE = 1
BLKCMD_ABORT = 10
BLKCMD_ACCEPT = 11
BLKCMD_ADDLIST = 12
BLKCMD_ADJOURN = 13
BLKCMD_ALLOBSERVERS = 14
BLKCMD_ASSESS = 15
BLKCMD_BACKWARD = 16
BLKCMD_BELL = 17
BLKCMD_BEST = 18
BLKCMD_BNAME = 19
BLKCMD_BOARDS = 20
BLKCMD_BSETUP = 21
BLKCMD_BUGWHO = 22
BLKCMD_CBEST = 23
BLKCMD_CLEARMESSAGES = 24
BLKCMD_CLRSQUARE = 25
BLKCMD_CONVERT_BCF = 26
BLKCMD_CONVERT_ELO = 27
BLKCMD_CONVERT_USCF = 28
BLKCMD_COPYGAME = 29
BLKCMD_CRANK = 30
BLKCMD_CSHOUT = 31
BLKCMD_DATE = 32
BLKCMD_DECLINE = 33
BLKCMD_DRAW = 34
BLKCMD_ECO = 35
BLKCMD_EXAMINE = 36
BLKCMD_FINGER = 37
BLKCMD_FLAG = 38
BLKCMD_FLIP = 39
BLKCMD_FMESSAGE = 40
BLKCMD_FOLLOW = 41
BLKCMD_FORWARD = 42
BLKCMD_GAMES = 43
BLKCMD_GETGI = 44
BLKCMD_GETPI = 45
BLKCMD_GINFO = 46
BLKCMD_GOBOARD = 47
BLKCMD_HANDLES = 48
BLKCMD_HBEST = 49
BLKCMD_HELP = 50
BLKCMD_HISTORY = 51
BLKCMD_HRANK = 52
BLKCMD_INCHANNEL = 53
BLKCMD_INDEX = 54
BLKCMD_INFO = 55
BLKCMD_ISET = 56
BLKCMD_IT = 57
BLKCMD_IVARIABLES = 58
BLKCMD_JKILL = 59
BLKCMD_JOURNAL = 60
BLKCMD_JSAVE = 61
BLKCMD_KIBITZ = 62
BLKCMD_LIMITS = 63
BLKCMD_LINE = 64 # Not on FICS
BLKCMD_LLOGONS = 65
BLKCMD_LOGONS = 66
BLKCMD_MAILHELP = 67
BLKCMD_MAILMESS = 68
BLKCMD_MAILMOVES = 69
BLKCMD_MAILOLDMOVES = 70
BLKCMD_MAILSOURCE = 71
BLKCMD_MAILSTORED = 72
BLKCMD_MATCH = 73
BLKCMD_MESSAGES = 74
BLKCMD_MEXAMINE = 75
BLKCMD_MORETIME = 76
BLKCMD_MOVES = 77
BLKCMD_NEWS = 78
BLKCMD_NEXT = 79
BLKCMD_OBSERVE = 80
BLKCMD_OLDMOVES = 81
BLKCMD_OLDSTORED = 82
BLKCMD_OPEN = 83
BLKCMD_PARTNER = 84
BLKCMD_PASSWORD = 85
BLKCMD_PAUSE = 86
BLKCMD_PENDING = 87
BLKCMD_PFOLLOW = 88
BLKCMD_POBSERVE = 89
BLKCMD_PREFRESH = 90
BLKCMD_PRIMARY = 91
BLKCMD_PROMOTE = 92
BLKCMD_PSTAT = 93
BLKCMD_PTELL = 94
BLKCMD_PTIME = 95
BLKCMD_QTELL = 96
BLKCMD_QUIT = 97
BLKCMD_RANK = 98
BLKCMD_RCOPYGAME = 99
BLKCMD_RFOLLOW = 100
BLKCMD_REFRESH = 101
BLKCMD_REMATCH = 102
BLKCMD_RESIGN = 103
BLKCMD_RESUME = 104
BLKCMD_REVERT = 105
BLKCMD_ROBSERVE = 106
BLKCMD_SAY = 107
BLKCMD_SERVERS = 108
BLKCMD_SET = 109
BLKCMD_SHOUT = 110
BLKCMD_SHOWLIST = 111
BLKCMD_SIMABORT = 112
BLKCMD_SIMALLABORT = 113
BLKCMD_SIMADJOURN = 114
BLKCMD_SIMALLADJOURN = 115
BLKCMD_SIMGAMES = 116
BLKCMD_SIMMATCH = 117
BLKCMD_SIMNEXT = 118
BLKCMD_SIMOBSERVE = 119
BLKCMD_SIMOPEN = 120
BLKCMD_SIMPASS = 121
BLKCMD_SIMPREV = 122
BLKCMD_SMOVES = 123
BLKCMD_SMPOSITION = 124
BLKCMD_SPOSITION = 125
BLKCMD_STATISTICS = 126
BLKCMD_STORED = 127
BLKCMD_STYLE = 128
BLKCMD_SWITCH = 130
BLKCMD_TAKEBACK = 131
BLKCMD_TELL = 132
BLKCMD_TIME = 133
BLKCMD_TOMOVE = 134
BLKCMD_TOURNSET = 135
BLKCMD_UNALIAS = 136
BLKCMD_UNEXAMINE = 137
BLKCMD_UNOBSERVE = 138
BLKCMD_UNPAUSE = 139
BLKCMD_UPTIME = 140
BLKCMD_USCF = 141
BLKCMD_USTAT = 142
BLKCMD_VARIABLES = 143
BLKCMD_WHENSHUT = 144
BLKCMD_WHISPER = 145
BLKCMD_WHO = 146
BLKCMD_WITHDRAW = 147
BLKCMD_WNAME = 148
BLKCMD_XKIBITZ = 149
BLKCMD_XTELL = 150
BLKCMD_XWHISPER = 151
BLKCMD_ZNOTIFY = 152
BLKCMD_REPLY = 153 # Not on FICS
BLKCMD_SUMMON = 154
BLKCMD_SEEK = 155
BLKCMD_UNSEEK = 156
BLKCMD_SOUGHT = 157
BLKCMD_PLAY = 158
BLKCMD_ALIAS = 159
BLKCMD_NEWBIES = 160
BLKCMD_SR = 161
BLKCMD_CA = 162
BLKCMD_TM = 163
BLKCMD_GETGAME = 164
BLKCMD_CCNEWSE = 165
BLKCMD_CCNEWSF = 166
BLKCMD_CCNEWSI = 167
BLKCMD_CCNEWSP = 168
BLKCMD_CCNEWST = 169
BLKCMD_CSNEWSE = 170
BLKCMD_CSNEWSF = 171
BLKCMD_CSNEWSI = 172
BLKCMD_CSNEWSP = 173
BLKCMD_CSNEWST = 174
BLKCMD_CTNEWSE = 175
BLKCMD_CTNEWSF = 176
BLKCMD_CTNEWSI = 177
BLKCMD_CTNEWSP = 178
BLKCMD_CTNEWST = 179
BLKCMD_CNEWS = 180
BLKCMD_SNEWS = 181
BLKCMD_TNEWS = 182
BLKCMD_RMATCH = 183
BLKCMD_RSTAT = 184
BLKCMD_CRSTAT = 185
BLKCMD_HRSTAT = 186
BLKCMD_GSTAT = 187

# Note admin codes start from 300.

BLKCMD_ERROR_BADCOMMAND = 512
BLKCMD_ERROR_BADPARAMS = 513
BLKCMD_ERROR_AMBIGUOUS = 514
BLKCMD_ERROR_RIGHTS = 515
BLKCMD_ERROR_OBSOLETE = 516
BLKCMD_ERROR_REMOVED = 517
BLKCMD_ERROR_NOTPLAYING = 518
BLKCMD_ERROR_NOSEQUENCE = 519
BLKCMD_ERROR_LENGTH = 520

LIMIT_BLKCMD_ERRORS=500

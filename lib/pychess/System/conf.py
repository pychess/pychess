""" The task of this module is to provide easy saving/loading of configurations
    It also supports gconf like connection, so you get notices when a property
    has changed. """
import sys
import os
import atexit
import builtins
import locale
from configparser import RawConfigParser

from pychess import MSYS2
from pychess.Utils.const import FISCHERRANDOMCHESS, LOSERSCHESS, COUNT_OF_SOUNDS, SOUND_MUTE
from pychess.System.Log import log
from pychess.System.prefix import addDataPrefix, addUserConfigPrefix, getDataPrefix

section = "General"
configParser = RawConfigParser(default_section=section)

for sect in ("FICS", "ICC"):
    if not configParser.has_section(sect):
        configParser.add_section(sect)

path = addUserConfigPrefix("config")
encoding = locale.getpreferredencoding()
if os.path.isfile(path):
    configParser.readfp(open(path, encoding=encoding))
atexit.register(lambda: configParser.write(open(path, "w", encoding=encoding)))

if sys.platform == "win32":
    username = os.environ["USERNAME"]
else:
    from os import getuid
    from pwd import getpwuid
    userdata = getpwuid(getuid())
    realname = userdata.pw_gecos.split(",")[0]
    if realname:
        username = realname
    else:
        username = userdata.pw_name

if getattr(sys, 'frozen', False) and not MSYS2:
    # pyinstaller specific!
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(sys.executable)
    default_book_path = os.path.join(base_path, "pychess_book.bin")
else:
    default_book_path = os.path.join(addDataPrefix("pychess_book.bin"))

no_gettext = False


idkeyfuncs = {}
conid = 0


def notify_add(key, func, *args, section=section):
    """The signature for func must be self, client, *args, **kwargs"""
    assert isinstance(key, str)
    global conid
    idkeyfuncs[conid] = (key, func, args, section)
    conid += 1
    return conid - 1


def notify_remove(conid):
    del idkeyfuncs[conid]


if "_" not in builtins.__dir__():
    def _(text):
        return text


DEFAULTS = {
    "General": {
        "firstName": username,
        "secondName": _("Guest"),
        "showEmt": False,
        "showEval": False,
        "showBlunder": True,
        "hideTabs": False,
        "closeAll": False,
        "faceToFace": False,
        "scoreLinearScale": False,
        "showCaptured": False,
        "figuresInNotation": False,
        "moveAnimation": False,
        "noAnimation": False,
        "autoPromote": False,
        "autoRotate": False,
        "showFICSgameno": False,
        "fullAnimation": True,
        "showCords": True,
        "drawGrid": True,
        "board_frame": 1,
        "board_style": 1,
        "pieceTheme": "Chessicons",
        "darkcolour": "",
        "lightcolour": "",
        "movetextFont": "FreeSerif Regular 12",
        "autoSave": True,
        "autoSavePath": os.path.expanduser("~"),
        "autoSaveFormat": "pychess",
        "saveEmt": False,
        "saveEval": False,
        "saveRatingChange": False,
        "indentPgn": False,
        "saveOwnGames": True,
        "dont_show_externals_at_startup": False,
        "max_analysis_spin": 3,
        "variation_threshold_spin": 50,
        "fromCurrent": True,
        "shouldWhite": True,
        "shouldBlack": True,
        "ThreatPV": False,
        "infinite_analysis": False,
        "opening_check": False,
        "opening_file_entry": default_book_path,
        "book_depth_max": 8,
        "endgame_check": False,
        "egtb_path": os.path.join(getDataPrefix()),
        "online_egtb_check": True,
        "autoCallFlag": True,
        "hint_mode": False,
        "spy_mode": False,
        "ana_combobox": 0,
        "analyzer_check": True,
        "inv_ana_combobox": 0,
        "inv_analyzer_check": False,
        "newgametasker_playercombo": 0,
        "ics_combo": 0,
        "autoLogin": False,
        "standard_toggle": True,
        "blitz_toggle": True,
        "lightning_toggle": True,
        "variant_toggle": True,
        "registered_toggle": True,
        "guest_toggle": True,
        "computer_toggle": True,
        "titled_toggle": True,
        "numberOfFingers": 0,
        "numberOfTimesLoggedInAsRegisteredUser": 0,
        "lastdifference-1": -1,
        "lastdifference-2": -1,
        "lastdifference-3": -1,
        "standard_toggle1": True,
        "blitz_toggle1": True,
        "lightning_toggle1": True,
        "variant_toggle1": True,
        "computer_toggle1": True,
        "categorycombo": 0,
        "learncombo0": 0,
        "learncombo1": 0,
        "learncombo2": 0,
        "learncombo3": 0,
        "welcome_image": addDataPrefix("glade/background.jpg"),
        "alarm_spin": 15,
        "show_tip_at_startup": True,
        "tips_seed": 0,
        "tips_index": 0,
        "dont_show_externals_at_startup": False,
        "download_timestamp": False,
        "download_chess_db": False,
        "download_scoutfish": False,
        "ngvariant1": FISCHERRANDOMCHESS,
        "ngvariant2": LOSERSCHESS,
        "useSounds": True,
        "max_log_files": 10,
        "show_sidepanels": True,
        "chat_paned_position": 100,
        "notimeRadio": 0,
        "blitzRadio": 0,
        "ngblitz min": 5,
        "ngblitz gain": 0,
        "ngblitz moves": 0,
        "rapidRadio": 0,
        "ngrapid min": 15,
        "ngrapid gain": 5,
        "ngrapid moves": 0,
        "normalRadio": 0,
        "ngnormal min": 45,
        "ngnormal gain": 15,
        "ngnormal moves": 0,
        "classicalRadio": 0,
        "playNormalRadio": 0,
        "playVariant1Radio": 0,
        "playVariant2Radio": 0,
        "ngclassical min": 3,
        "ngclassical gain": 0,
        "ngclassical moves": 40,
        "whitePlayerCombobox": 0,
        "blackPlayerCombobox": 0,
        "skillSlider1": 20,
        "skillSlider2": 20,
        "taskerSkillSlider": 20,
        "seek1Radio": 0,
        "seek2Radio": 0,
        "seek3Radio": 0,
        "challenge1Radio": 0,
        "challenge2Radio": 0,
        "challenge3Radio": 0,
    },
    "FICS": {
        "timesealCheck": True,
        "hostEntry": "freechess.org",
        "usernameEntry": "",
        "passwordEntry": "",
        "asGuestCheck": True,
    },
    "ICC": {
        "timesealCheck": True,
        "hostEntry": "chessclub.com",
        "usernameEntry": "",
        "passwordEntry": "",
        "asGuestCheck": True,
    },
}

for i in range(COUNT_OF_SOUNDS):
    DEFAULTS["General"]["soundcombo%d" % i] = SOUND_MUTE
    DEFAULTS["General"]["sounduri%d" % i] = ""


def get(key, section=section):
    try:
        default = DEFAULTS[section][key]
    except KeyError:
        # window attributes has no default values
        # print("!!! conf get() KeyError: %s %s" % (section, key))
        default = None

    try:
        value = configParser.getint(section, key, fallback=default)
        # print("... conf get %s %s: %s" % (section, key, value))
        return value
    except ValueError:
        pass

    try:
        value = configParser.getboolean(section, key, fallback=default)
        # print("... conf get %s %s: %s" % (section, key, value))
        return value
    except ValueError:
        pass

    try:
        value = configParser.getfloat(section, key, fallback=default)
        # print("... conf get %s %s: %s" % (section, key, value))
        return value
    except ValueError:
        pass

    value = configParser.get(section, key, fallback=default)
    # print("... conf get %s %s: %s" % (section, key, value))
    return value


def set(key, value, section=section):
    # print("---conf set()", section, key, value)
    try:
        configParser.set(section, key, str(value))
        configParser.write(open(path, "w"))
    except Exception as err:
        log.error(
            "Unable to save configuration '%s'='%s' because of error: %s %s" %
            (repr(key), repr(value), err.__class__.__name__, ", ".join(
                str(a) for a in err.args)))
    for key_, func, args, section_ in idkeyfuncs.values():
        if key_ == key and section_ == section:
            func(None, *args)


def hasKey(key, section=section):
    return configParser.has_option(section, key)

import os
import atexit
import gettext
import sqlite3

from pychess.System import conf
from pychess.System.prefix import addDataPrefix, isInstalled

ECO_MAIN_LANG = "en"
ECO_LANGS = [ECO_MAIN_LANG, "da", "de", "es", "hu", "fr"]

# EN = https://github.com/niklasf/eco
# DA = https://da.wikipedia.org/wiki/Skak%C3%A5bninger
# DE = https://de.wikipedia.org/wiki/ECO-Code
# ES = https://es.wikipedia.org/wiki/Anexo:Aperturas_de_ajedrez
# HU = https://hu.wikipedia.org/wiki/Sakkmegnyit%C3%A1sok_list%C3%A1ja
# FR = https://fr.wikipedia.org/wiki/Liste_des_ouvertures_d'%C3%A9checs_suivant_le_code_ECO

db_path = os.path.join(addDataPrefix("eco.db"))
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    atexit.register(conn.close)
    ECO_OK = True
else:
    print("Warning: eco.db not found, please run pgn2ecodb.sh")
    ECO_OK = False

if isInstalled():
    mofile = gettext.find("pychess")
else:
    mofile = gettext.find("pychess", localedir=addDataPrefix("lang"))

if mofile is None:
    lang = ECO_MAIN_LANG
else:
    lang = mofile.split(os.sep)[-3]


def get_eco(hash, exactPosition=True):
    if not ECO_OK:
        return None
    cur = conn.cursor()
    select = "select eco, opening, variation, endline from openings where hash=? and hkey=? and lang=? and endline like ?"
    qh = hex(hash)[2:]
    qhkey = int(qh[-2:], 16)
    qlang = ECO_MAIN_LANG if conf.no_gettext or lang not in ECO_LANGS else lang
    qpos = 1 if exactPosition else "%"
    cur.execute(select, (qh, qhkey, qlang, qpos))
    result = cur.fetchone()
    if result is None and qlang != ECO_MAIN_LANG:
        cur.execute(select, (qh, qhkey, ECO_MAIN_LANG, qpos))
        result = cur.fetchone()
    return result


def find_opening_fen(keyword):
    # Checks
    if not ECO_OK:
        return None
    if keyword is None:
        return None
    keyword = keyword.strip()
    if keyword == "":
        return None
    cur = conn.cursor()

    # Languages to check
    langs = [ECO_MAIN_LANG]
    lang = os.getenv("LANG", ECO_MAIN_LANG).lower()
    if lang in ECO_LANGS and lang != ECO_MAIN_LANG:
        langs = [lang] + langs

    # Execute the check
    for lang in langs:
        # Lookup by ECO
        query = "select fen from openings   \
                 where mainline = 1          \
                   and endline = 1            \
                   and eco = ?                 \
                   and lang = ?"
        cur.execute(query, (keyword.upper(), lang))
        result = cur.fetchone()
        if result is not None:
            return result[0]

        # Lookup by detailed name
        query = "select fen from openings               \
                 where endline = 1                       \
                   and lang = ?                           \
                   and (  lower(opening) like ?            \
                       or lower(variation) like ?           \
                   )                                         \
                 order by eco, opening, length(variation)     \
                 limit 1"
        kwenh = ("%%%s%%" % keyword.lower()).replace("*", "%")
        cur.execute(query, (lang, kwenh, kwenh))
        result = cur.fetchone()
        if result is not None:
            return result[0]

    # Nothing found
    return None

import os
import atexit
import gettext
import sqlite3
import struct

from pychess.System import conf
from pychess.System.prefix import addDataPrefix, isInstalled

db_path = os.path.join(addDataPrefix("eco.db"))
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    atexit.register(conn.close)
    ECO_OK = True
else:
    print("Warning: eco.db not found, please run pgn2ecodb.sh")
    ECO_OK = False

if isInstalled():
    mofile = gettext.find('pychess')
else:
    mofile = gettext.find('pychess', localedir=addDataPrefix("lang"))

if mofile is None:
    lang = "en"
else:
    lang = mofile.split(os.sep)[-3]

# big-endian, unsigned long long (uint64)
hash_struct = struct.Struct('>Q')


def get_eco(hash):
    if not ECO_OK:
        return None
    cur = conn.cursor()
    select = "select eco, opening, variation from openings where hash=? and lang=?"
    cur.execute(select, (memoryview(hash_struct.pack(hash)), "en" if conf.no_gettext or lang not in ("da", "de", "es", "hu") else lang))
    return cur.fetchone()

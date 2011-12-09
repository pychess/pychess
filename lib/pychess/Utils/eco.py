import os
import atexit
import gettext
import sqlite3

from pychess.System.prefix import addDataPrefix

path = os.path.join(addDataPrefix("eco.db"))
conn = sqlite3.connect(path, check_same_thread = False)

atexit.register(conn.close)

mofile = gettext.find('pychess', localedir=addDataPrefix("lang"))
if mofile is None:
    lang = "en"
else:
    lang = mofile.split(os.sep)[-3]

def get_eco(hash):
    cur = conn.cursor()
    select = "select eco, opening, variation from openings where hash=? and lang=?"
    cur.execute(select, (buffer(hex(hash)), lang))
    return cur.fetchone()
    

import os
import atexit
import gettext
import sqlite3

from pychess.System.prefix import addDataPrefix

path = os.path.join(addDataPrefix("eco.db"))
conn = sqlite3.connect(path, check_same_thread = False)

atexit.register(conn.close)

mofile = gettext.find('pychess')
if mofile is None:
    lang = "en"
else:
    lang = mofile.split(os.sep)[-3]

def get_eco(fen):
    cur = conn.cursor()
    cur.execute("select eco, name from openings where fen='%s' and lang='%s'" % (fen, lang))
    row = cur.fetchone()
    return row
    

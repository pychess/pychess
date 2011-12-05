import os
import atexit
import locale
import sqlite3

from pychess.System.prefix import addDataPrefix

path = os.path.join(addDataPrefix("eco.db"))
conn = sqlite3.connect(path, check_same_thread = False)

atexit.register(conn.close)

lang = locale.getdefaultlocale()[0][:2]


def get_eco(fen):
    cur = conn.cursor()
    cur.execute("select eco, name from openings where fen='%s' and lang='%s'" % (fen, lang))
    row = cur.fetchone()
    return row
    

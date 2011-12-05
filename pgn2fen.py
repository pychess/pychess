# English eco.pgn was converted from
# http://www.chessville.com/downloads_files/instructional_materials/ECO_Codes_With_Names_and_Moves.zip
# others from wikipedia

import os
import sys
import sqlite3

from pychess.Savers.pgn import load
from pychess.System.prefix import addDataPrefix

path = os.path.join(addDataPrefix("eco.db"))
conn = sqlite3.connect(path)

if __name__ == '__main__':
    c = conn.cursor()

    c.execute("drop table if exists openings")
    c.execute("create table openings(hash blob, base integer, eco text, lang text, name text)")

    def feed(pgnfile, lang):
        cf = load(open(pgnfile))
        rows = []
        old_eco = ""
        for i, game in enumerate(cf.games):
            model = cf.loadToModel(i, quick_parse=True)

            eco = cf._getTag(i, "ECO")[:3]
            name = ""

            opening = cf._getTag(i, "Opening")
            if opening is not None:
                name += opening

            variation = cf._getTag(i, "Variation")
            if variation is not None:
                if name:
                    name += ", "
                name += variation
            
            base = int(old_eco != eco)
            
            if len(model.moves) == 0:
                cu = conn.cursor()
                cu.execute("select * from openings where eco=? and lang='en' and base=1", (eco,))
                res = cu.fetchone()
                if res is not None:
                    hash = res[0]
            else:
                hash = buffer(hex(model.boards[-1].board.hash))
                
            if name:
                rows.append((hash, base, eco, lang, name))
                
            old_eco = eco
                
        c.executemany("insert into openings(hash, base, eco, lang, name) values (?, ?, ?, ?, ?)", rows)
        conn.commit()

    # Several eco list contains only eco+name pairs, so
    # we will use base ECO line positions from en eco.pgn 
    print "processing en eco.pgn"
    feed("lang/en/eco.pgn", "en")
    
    for lang in [d for d in os.listdir("lang") if os.path.isdir("lang/"+d)]:
        if lang == "en":
            continue
            
        pgnfile = "lang/%s/eco.pgn" % lang
        if os.path.isfile(pgnfile):
            print "processing %s eco.pgn" % lang
            feed(pgnfile, lang)

    conn.close()

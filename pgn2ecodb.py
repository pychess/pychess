# English eco.pgn was converted from
# http://www.chessville.com/downloads_files/instructional_materials/ECO_Codes_With_Names_and_Moves.zip
# others from wikipedia

import os
import sqlite3

from pychess.Database.PgnImport import PgnImport
from pychess.Savers.pgn import load
from pychess.System.protoopen import protoopen
from pychess.System.prefix import addDataPrefix
from pychess.Utils.eco import hash_struct


path = os.path.join(addDataPrefix("eco.db"))
conn = sqlite3.connect(path)

if __name__ == '__main__':
    c = conn.cursor()

    c.execute("drop table if exists openings")

    # Unfortunately sqlite doesn't support uint64, so we have to use blob type to store polyglot-hash values
    c.execute("create table openings(hash blob, base integer, eco text, lang text, opening text, variation text)")

    def feed(pgnfile, lang):
        cf = load(protoopen(pgnfile))
        cf.limit = 5000
        importer = PgnImport(cf)
        cf.init_tag_database(importer)
        records, plys = cf.get_records()

        rows = []
        old_eco = ""
        for rec in records:
            model = cf.loadToModel(rec)

            eco = rec["ECO"]

            opening = rec["White"]
            if opening is None:
                opening = ""

            variation = rec["Black"]
            if variation is None:
                variation = ""

            base = int(old_eco != eco)

            ply = len(model.moves)
            if ply == 0:
                cu = conn.cursor()
                cu.execute("select * from openings where eco=? and lang='en' and base=1", (eco,))
                res = cu.fetchone()
                if res is not None:
                    hash = res[0]
            else:
                hash = memoryview(hash_struct.pack(model.boards[-1].board.hash))

            if opening:
                rows.append((hash, base, eco, lang, opening, variation))

            old_eco = eco

        c.executemany("insert into openings(hash, base, eco, lang, opening, variation) values (?, ?, ?, ?, ?, ?)", rows)
        conn.commit()

    # Several eco list contains only eco+name pairs, so
    # we will use base ECO line positions from en eco.pgn
    print("processing en eco.pgn")
    feed("lang/en/eco.pgn", "en")

    for lang in [d for d in os.listdir("lang") if os.path.isdir("lang/" + d)]:
        if lang == "en":
            continue

        pgnfile = "lang/%s/eco.pgn" % lang
        if os.path.isfile(pgnfile):
            print("processing %s eco.pgn" % lang)
            feed(pgnfile, lang)

    conn.close()

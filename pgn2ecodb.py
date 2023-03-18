# An opening book needs to be built as follows:
#   - install "pgn-extract" and "polyglot"
#   - collect many relevant games into a single PGN file "input.pgn"
#   - remove the variant games (960, atomic...) from the file
#   - solve the errors given by: pgn-extract -s -r input.pgn
#   - create a file as "filter.txt":
#           WhiteElo >= "1800"
#           BlackElo >= "1800"
#   - extract the best games: pgn-extract -tfilter.txt --notags --nocomments --nonags --novars -bl20 --plylimit 26 -s -owip.pgn input.pgn
#   - create the opening book: polyglot make-book -min-game 10 -pgn wip.pgn -bin pychess_book.bin
#   - merge the books (if needed): polyglot merge-book -in1 book1.bin -in2 book2.bin -out book.bin
#
# The opening book does not contain the names. They are stored in the separate file "eco.db" by
# running the current script. If a name refers to a position that is not part of the opening book,
# it cannot be displayed. If it refers to a shared position, the name is selected according to some
# priority rules. The source ECO file must also be sorted by ECO (at least) to be able to load the
# other languages.
#
# The current book supports 99.5% of the ECO names written in English.

import sys
import os
import sqlite3

from pychess.Savers.pgn import load
from pychess.System.protoopen import protoopen
from pychess.System.prefix import addDataPrefix
from pychess.Utils.eco import ECO_MAIN_LANG, ECO_LANGS
from pychess.Variants.fischerandom import FischerandomBoard


path = os.path.join(addDataPrefix("eco.db"))
conn = sqlite3.connect(path)

if __name__ == "__main__":
    print("Creating the database")
    c = conn.cursor()
    c.execute("drop table if exists openings")
    c.execute(
        "create table openings (hash text, hkey integer, mainline integer, endline integer, eco text, lang text, opening text, variation text, fen text)"
    )
    c.execute("create index if not exists openings_index on openings (hkey)")

    def feed(pgnfile, lang):
        # Check the existence of the file
        if not os.path.isfile(pgnfile):
            return

        # Load the ECO file first
        print("  - Parsing")
        cf = load(protoopen(pgnfile))
        cf.limit = 5000
        cf.init_tag_database()
        records, plys = cf.get_records()

        # Cache the content
        entries = []
        plyMax = 0
        old_eco = ""
        for rec in records:
            model = cf.loadToModel(rec)
            eco = "" if rec["ECO"] is None else rec["ECO"]
            entry = {
                "h": [],  # Hashes
                "f": "",  # Final hash of the line
                "n": [],  # FENs
                "m": old_eco
                != eco,  # Main line = shortest sequence of moves for the ECO code. The 'EN' ECO file is specially crafted
                "e": eco,  # ECO
                "o": "" if rec["White"] is None else rec["White"],  # Opening
                "v": "" if rec["Black"] is None else rec["Black"],  # Variation
                "p": len(model.moves),
            }  # Number of plies
            plyMax = max(plyMax, entry["p"])

            # No move means that we are translating the name of the ECO code, so we need to find all the related positions from another language
            if entry["p"] == 0:
                if lang == ECO_MAIN_LANG:
                    continue
                c.execute(
                    "select hash, endline, fen from openings where eco=? and lang=? and mainline=1",
                    (eco, ECO_MAIN_LANG),
                )
                rows = c.fetchall()
                for row in rows:
                    entry["h"].append(row[0])
                    if row[1] == int(True):
                        entry["f"] = row[0]
                    entry["n"].append(row[2])
            else:
                # Find the Polyglot hash for each position of the opening
                for i in range(entry["p"]):
                    nextboard = model.getBoardAtPly(i, 0).board.next
                    h = hex(nextboard.hash)[2:]
                    entry["h"].append(h)
                    entry["f"] = h
                    entry["n"].append(nextboard.asFen())
            entries.append(entry)
            old_eco = entry["e"]
        print("  - Max ply : %d" % plyMax)

        # Process all the data in reverse order
        for depth in reversed(range(plyMax + 1)):
            sys.stdout.write("\r  - Loading into the database (%d remaining)  " % depth)
            sys.stdout.flush()
            for i in reversed(
                range(len(entries))
            ):  # Long lines are overwritten by short lines
                entry = entries[i]
                if entry["p"] != depth:
                    continue
                for i in range(len(entry["h"])):
                    h = entry["h"][i]
                    hkey = int(h[-2:], 16)
                    c.execute(
                        "select endline from openings where hash=? and hkey=? and lang=?",
                        (h, hkey, lang),
                    )
                    r = c.fetchone()
                    if r is not None and r[0] == int(True):
                        continue
                    c.execute(
                        "delete from openings where hash=? and hkey=? and lang=?",
                        (h, hkey, lang),
                    )
                    c.execute(
                        "insert into openings (hash, hkey, mainline, endline, eco, lang, opening, variation, fen) values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            h,
                            hkey,
                            int(entry["m"]),
                            int(h == entry["f"]),
                            entry["e"],
                            lang,
                            entry["o"],
                            entry["v"],
                            entry["n"][i],
                        ),
                    )
        conn.commit()
        print("\n  - Processed %d openings" % len(entries))

    # Several eco lists contain only eco+name pairs
    # We use the base ECO line positions from EN/eco.pgn
    # English is first in ECO_LANGS for that reason
    for lang in ECO_LANGS:
        print("Processing %s" % lang.upper())
        feed("lang/%s/eco.pgn" % lang, lang)

    # Start positions for Chess960
    print("Processing Chess960")
    chess960 = FischerandomBoard()
    for i in range(960):
        c.execute(
            "insert into openings (mainline, endline, eco, lang, opening, fen) values (?, '1', '960', ?, ?, ?)",
            (
                "1" if i == 518 else "0",
                ECO_MAIN_LANG,
                "Chess%.3d" % (i + 1),
                chess960.getFrcFen(i + 1),
            ),
        )
    conn.close()

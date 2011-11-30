import os
import sys

from pychess.Savers.pgn import load


# http://www.chessville.com/downloads_files/instructional_materials/ECO_Opening_Variations.zip
if __name__ == '__main__':
    pgnfile = sys.argv[1] if len(sys.argv) > 1 else ""
    if os.path.isfile(pgnfile):
        ecofile = file("eco.py", "w")
        cf = load(open(pgnfile))
        print >> ecofile, "eco_lookup = {"
        for i, game in enumerate(cf.games):
            model = cf.loadToModel(i, quick_parse=True)
            fen = model.boards[-1].asFen()
            eco = cf._getTag(i, "ECO")[:3]
            names = ""

            opening = cf._getTag(i, "Opening")
            if opening is not None:
                for tag in opening.split(', '):
                    if tag[0].isdigit():
                        names += '"%s",' % tag
                    else:
                        names += '_("%s"),' % tag

            variation = cf._getTag(i, "Variation")
            if variation is not None:
                for tag in variation.split(', '):
                    if tag[0].isdigit():
                        names += '"%s",' % tag
                    else:
                        names += '_("%s"),' % tag
            if names:
                print >> ecofile, '"%s": ("%s", (%s)),' % (fen, eco, names)
        print >> ecofile, "}"
        ecofile.close()

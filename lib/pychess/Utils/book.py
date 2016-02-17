from __future__ import print_function

import os
import sys
from struct import Struct
from collections import namedtuple

from pychess.System import conf
from pychess.System.prefix import addDataPrefix
from pychess.Utils.lutils.lmove import parsePolyglot
from pychess.System.Log import log

if getattr(sys, 'frozen', False):
    # pyinstaller specific!
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(sys.executable)
    default_path = os.path.join(base_path, "pychess_book.bin")
else:
    default_path = os.path.join(addDataPrefix("pychess_book.bin"))

path = conf.get("opening_file_entry", default_path)

if os.path.isfile(path):
    bookfile = True
else:
    bookfile = False
    log.warning("Could not find %s" % path)

# The book probing code is based on that of PolyGlot by Fabien Letouzey.
# PolyGlot is available under the GNU GPL from http://wbec-ridderkerk.nl

BookEntry = namedtuple('BookEntry', 'key move weight games score')
# 'key' c_uint64      the position's hash
# 'move' c_uint16     the candidate move
# 'weight' c_uint16   proportional to prob. we should play it
# The following terms are not always available:
# 'games' c_uint16    the number of times it's been tried
# 'score' c_uint16    2 for each win, 1 for each draw

entrystruct = Struct(">QHHHH")
entrysize = entrystruct.size


def getOpenings(board):
    """ Return a tuple (move, weight, games, score) for each opening move
        in the given position. The weight is proportional to the probability
        that a move should be played. By convention, games is the number of
        times a move has been tried, and score the number of points it has
        scored (with 2 per victory and 1 per draw). However, opening books
        aren't required to keep this information. """

    openings = []
    if not bookfile:
        return openings

    with open(path, "rb") as bookFile:
        key = board.hash
        # Find the first entry whose key is >= the position's hash
        bookFile.seek(0, os.SEEK_END)
        low, high = 0, bookFile.tell() // 16 - 1
        if high < 0:
            return openings
        while low < high:
            mid = (low + high) // 2
            bookFile.seek(mid * 16)
            entry = bookFile.read(entrysize)
            if len(entry) != entrysize:
                return openings
            entry = BookEntry._make(entrystruct.unpack(entry))
            if entry.key < key:
                low = mid + 1
            else:
                high = mid

        bookFile.seek(low * 16)
        while True:
            entry = bookFile.read(entrysize)
            if len(entry) != entrysize:
                return openings
            entry = BookEntry._make(entrystruct.unpack(entry))
            if entry.key != key:
                break
            move = parsePolyglot(board, entry.move)
            openings.append((move, entry.weight, entry.games, entry.score))
    return openings

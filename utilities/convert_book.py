import __builtin__
__builtin__.__dict__['_'] = lambda s: s

import os.path

from pychess.Utils.const import NORMALCHESS, FEN_START
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import parseSAN, toPolyglot
from pychess.Utils.book import fen, getOpenings
from pychess.System.tsqlite import execSQL
from operator import attrgetter
from ctypes import *

bookFileName = "pychess_book.bin"

class BookEntry(BigEndianStructure):
    _fields_ = [ ('key', c_uint64),    # the position's hash
                 ('move', c_uint16),   # the candidate move
                 ('weight', c_uint16), # proportional to prob. we should play it
                 # The following terms are not always available:
                 ('games', c_uint16),  # the number of times it's been tried
                 ('score', c_uint16)   # 2 for each win, 1 for each draw
               ]

unvisitedFens = set()
visitedHashes = set()
bookEntries = list()
basePositions = 0
for (partialFen,) in execSQL ("select fen from openings"):
    unvisitedFens.add(partialFen)

def visit (board):
    global unvisitedFens, visitedHashes, bookEntries, basePositions
    if board.hash in visitedHashes:
        return
    visitedHashes.add(board.hash)
    firstHit = True
    for movestr, wins, draws, loses in getOpenings(board):
        if firstHit:
            basePositions += 1
            partialFen = fen(board)
            if partialFen in unvisitedFens:
                unvisitedFens.remove(partialFen)
            else:
                print "Inexact transposition reached:", board.asFen()
            firstHit = False
        move = parseSAN(board, movestr)
        k = board.hash
        m = toPolyglot(board, move)
        w = 3 * wins + draws # The same weight the PyChess engine uses
        g = wins + draws + loses
        s = 2 * wins + draws
        bookEntries.append(BookEntry(k, m, w, g, s))
        child = board.clone()
        child.applyMove(move)
        visit(child)

startpos = LBoard(NORMALCHESS)
startpos.applyFen(FEN_START)
visit(startpos)

print "Statistics:"
print "Book entries created:", len(bookEntries)
print "Positions with book moves:", basePositions
print "Positions MISSING in exported book:", len(unvisitedFens)
for partialFen in unvisitedFens:
    print partialFen

bookEntries.sort(key=attrgetter('weight'), reverse=True)
bookEntries.sort(key=attrgetter('key'))

print "Exporing book to", bookFileName
bookFile = open(bookFileName, "wb")
for entry in bookEntries:
    bookFile.write(entry)
bookFile.close()

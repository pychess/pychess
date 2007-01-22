import __builtin__
__builtin__.__dict__['_'] = lambda s: s

from pychess.Utils.lutils.LBoard import LBoard, FEN_START
from pychess.Utils.lutils.bitboard import toString
from pychess.Utils.lutils.ldata import *
from pychess.Utils.lutils.lsearch import alphaBeta
from pychess.Utils.lutils.leval import evaluateComplete

from pychess.Utils.lutils.lmove import toSAN
from pychess.Utils.const import *

from sys import maxint

board = LBoard()
board.applyFen (FEN_START)

try:
    import psyco
    psyco.bind(alphaBeta)
except ImportError:
    print "You do not have psyco installed. \n\
    If you do so, pychessengine can calculate moves at nearly the double speed"
    
if 0:
    from profile import runctx
    runctx ("mvs, scr = alphaBeta (board, 5, -maxint, maxint)", locals(), globals(), "/tmp/pychessprofile")
    from pstats import Stats
    s = Stats("/tmp/pychessprofile")
    s.sort_stats("cumulative")
    s.print_stats()
else:
    from time import time
    t = time()
    mvs, scr = alphaBeta (board, 5, -maxint, maxint)
    print time()-t

from pychess.Utils.lutils import lsearch
print lsearch.nodes

for move in mvs:
    print toSAN(board, move)
    board.applyMove(move)
    
for move in mvs:
    board.popMove()

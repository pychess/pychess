#!/usr/bin/python

from pychess.Utils.const import *

features = {
    "setboard": 1,
    "analyze": 1,
    "usermove": 1,
    "reuse": 0,
    "draw": 1,
    "sigterm": 1,
    "myname": "PyChess %s" % VERSION
}

print "feature %s done=0" % \
            " ".join(["=".join([k,repr(v)]) for k,v in features.iteritems()])

from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE, TYPE_PYOBJECT
from time import time
import sys, os
import thread
from threading import Lock

from Engine import Engine
from pychess.Utils.History import hisPool
from pychess.Utils.Move import movePool, parseSAN, parseAN, toAN, ParsingError
from pychess.Utils import eval
from pychess.Utils.book import getOpenings
from pychess.Utils.validator import findMoves2, isCheck
from pychess.Utils.History import History
from pychess.System.ThreadPool import pool
from pychess.Utils.TranspositionTable import TranspositionTable
from sys import maxint

from pychess.Utils.const import prefix
import gettext
gettext.install("pychess", localedir=prefix("lang"), unicode=1)
from pychess.Savers import epd
from cStringIO import StringIO

import random
def getBestOpening (board):
    score = 0
    move = None
    for m, w, d, l in getOpenings(board):
        s = (w+d/3.0)*random.random()
        if not move or s > score:
            move = m
            score = s
    return move

def nextedIterator (*items):
    used = set()
    for item in items:
       for i in item:
            if not i in used:
                used.add(i)
                yield i

last = 0
nodes = 0
searching = False
searchLock = Lock()

def alphaBeta (table, board, depth, alpha, beta, capture=False):
    """ This is a alphabeta/negamax/quiscent/iterativedeepend search algorithm
        Based on moves found by the validator.py findmoves2 function and
        evaluated by eval.py.
        
        The function recalls itself "depth" times. If the last move in range
        depth was a capture, it will continue calling itelf, only searching for
        captures.
        
        It returns a tuple of
        *   a list of the path it found through the search tree (last item being
            the deepest)
        *   a score of your standing the the last possition. """
    
    global last, nodes, searching
    foundPv = False
    hashf = hashfALPHA
    amove = []
    
    probe = table.probe (board, max(depth,1), alpha, beta)
    if probe: last = -1; return probe
    
    if (depth <= 0 and not capture) or depth < -2 or not searching:
        last = 1; result = [], eval.evaluateComplete(board, board.color)
        table.record (board, result[0], len(result[0]), result[1], hashfEXACT)
        return result
    
    # TODO: This doesn't work. Gives illegal moves. What should be changed?
    #lowerDepthMove = None
    #i = -1
    #while depth+i >= 1:
    #    probe = table.probe (board, depth+i, alpha, beta)
    #    if probe and probe[0]:
    #        lowerDepthMove = probe[0][0]
    #        break
    #    i -= 1
    
    # TODO: Use the killer move method.
    # *  Create a LimitedDict for each call (not the recursive ones)
    # *  Save [depth] = [move,] for each recursive call
    # *  Test each best move from other paths, before generating your own.
    # *  Remember to validate
    # *  Remember to test if this actually makes a difference (in best case alphabeta should only test a squareroot of the moves)
    
    # Would sorting moves by a simple evaluation (only piecevalue and location) help?
    
    pureCaptures = depth <= 0
    #if lowerDepthMove:
    #    iterator = nextedIterator([lowerDepthMove],
    #            findMoves2(board, pureCaptures=pureCaptures))
    #else: iterator = findMoves2(board, pureCaptures=pureCaptures)
    
    move = None
    for move in findMoves2(board, pureCaptures=pureCaptures):

        nodes += 1
        
        board2 = board.move(move)
            
        if board[move.cord1] != None:
            tempcapture = True
        else: tempcapture = False
        
        if foundPv:
            mvs, val = alphaBeta ( table, board2, depth-1,
                                   -alpha-1, -alpha, tempcapture)
            val = -val
            if val > alpha and val < beta:
                map(movePool.add, mvs)
                mvs, val = alphaBeta ( table, board2, depth-1,
                                       -beta, -alpha, tempcapture)
                val = -val
        else:
            mvs, val = alphaBeta ( table, board2, depth-1,
                                   -beta, -alpha, tempcapture)
            val = -val
        
        if val >= beta:
            table.record (board, [move]+mvs, len(mvs)+1, beta, hashfBETA)
            last = 3; return [move]+mvs, beta

        if val > alpha:
            map(movePool.add, amove)
            alpha = val
            amove = [move]+mvs
            hashf = hashfEXACT
            foundPv = True
        else:
            map(movePool.add, mvs)
    
    if amove: last = 4; result = (amove, alpha)
    elif not move:
        # If not moves were found, this must be a mate or stalemate
        lastn = 5
        if isCheck (board, board.color):
            result = ([], -maxint)
        else: result = ([], 0)
    else:
        # If not move made it through alphabeta (should not be possible)
        # We simply pick the last the best, whith th lowest score...
        last = 6; result = ([move], alpha)
    table.record (board, result[0], len(result[0]), result[1], hashf)
    return result

sd = 4
moves = None
increment = None
mytime = None
#optime = None
forced = False
analyzing = False

history = History()
table = TranspositionTable(50000)

def analyze2 ():
    from profile import runctx
    runctx ("analyze2()", locals(), globals(), "/tmp/pychessprofile")
    from pstats import Stats
    s = Stats("/tmp/pychessprofile")
    s.sort_stats("time")
    s.print_stats()

def analyze ():
    global searching, nodes
    searching = True
    start = time()
    searchLock.acquire()
    board = history[-1]
    for depth in range (1, 10):
        if not searching: break
        mvs, scr = alphaBeta (table, board, depth, -maxint, maxint)
        
        tempboard = board
        smvs = []
        for move in mvs:
            smvs.append(toAN (tempboard, move))
            tempboard = tempboard.move(move)
        smvs = " ".join(smvs)
        
        print depth,"\t", "%0.2f" % (time()-start),"\t", scr,"\t", nodes,"\t", smvs
        nodes = 0
    searchLock.release()
    
def go ():
    # TODO: Length info should be put in the book.
    # Btw. 10 is not enough. Try 20
    if len(history) < 14:
        movestr = getBestOpening(history[-1])
        if movestr:
            move = parseSAN(history[-1], movestr)
        
    if len(history) >= 14 or not movestr:
        
        searchLock.acquire()
        global searching, nodes, mytime, increment
        searching = True
        
        if mytime == None:
            mvs, scr = alphaBeta (table, history[-1], sd, -maxint, maxint)
            move = mvs[0]
        
        else:
            # We bet that the game will be about 30 moves. That gives us
            # starttime / 30 seconds per turn + the incremnt.
            # TODO: Create more sophisticated method.
            usetime = float(mytime) / max((30-len(history)),3)
            usetime = max (usetime, 5) # We don't wan't to search for e.g. 0 secs
            starttime = time()
            endtime = starttime + usetime
            print "Time left: %d seconds; Thinking for %d seconds" % (mytime, usetime)
            for depth in range(sd):
                mvs, scr = alphaBeta (table, history[-1], depth, -maxint, maxint)
                if time() > endtime: break
            move = mvs[0]
            mytime -= time() - starttime
            mytime += increment
        
        print "moves were", mvs, \
              "color is", history[-1].color, history.curCol(), \
              "last", last
        
        nodes = 0
        searching = False
        searchLock.release()
        
    history.add(move, mvlist=False)
    print "move", toAN(history[-2], move)

while True:
    line = raw_input()
    lines = line.split()
    
    if lines[0] == "protover":
        print "features done=1"
    
    elif lines[0] == "usermove":
        
        if analyzing:
            searching = False
            searchLock.acquire()
            searchLock.release()
        
        try:
            move = parseAN (history[-1], lines[1])
        except ParsingError:
            print "Illegal move:", repr(lines[1])
            sys.exit(os.EX_PROTOCOL)
            
        history.add(move, mvlist=False)
        
        if not forced and not analyzing:
            thread.start_new(go,())
        
        if analyzing:
            thread.start_new(analyze,())
        
    elif lines[0] == "sd":
        sd = int(lines[1])
        if sd < 4: sd = 1
        if 4 <= sd <= 7: sd = 2
        if 7 < sd: sd = 3
        
    elif lines[0] == "level":
        moves = int(lines[1])
        increment = int(lines[3])
        minutes = lines[2].split(":")
        mytime = int(minutes[0])*60
        if len(minutes) > 1:
            mytime += int(minutes[1])
        print "Playing %d moves in %d seconds + %d increment" % (moves, mytime, increment)
    
    elif lines[0] == "time":
        mytime = int(lines[1])
    
    #elif lines[0] == "otim":
    #   optime = int(lines[1])
    
    elif lines[0] == "quit":
        sys.exit()
    
    elif lines[0] == "force":
        forced = True
        
    elif lines[0] == "go":
        forced = False
        thread.start_new(go,())
        
    elif lines[0] in ("black", "white"):
        searching = False
        searchLock.acquire()
        newColor = lines[0] == "black" and BLACK or WHITE
        if history.curCol() != newColor:
            history.setStartingColor(1-history[0].color)
        searchLock.release()
        if analyzing:
            thread.start_new(analyze,())
    
    elif lines[0] == "analyze":
        analyzing = True
        thread.start_new(analyze,())
        
    elif lines[0] == "draw":
        print "offer draw"
    
    elif lines[0] == "setboard":
        searching = False
        io = StringIO()
        io.write(" ".join(lines[1:])+"\n")
        io.seek(0)
        epdfile = epd.load(io)
        io.close()
        searchLock.acquire()
        history = epdfile.loadToHistory(0,-1)
        searchLock.release()
        if analyzing:
            thread.start_new(analyze,())
    
    elif lines[0] in ("xboard", "otim", "hard", "easy" "nopost", "post"):
        pass
    
    else: print "Error (unknown command):", line

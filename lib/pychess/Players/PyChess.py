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
from pychess.Utils.book import getOpenings
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

searching = False
searchLock = Lock()

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
    #s.sort_stats("time")
    s.sort_stats("cumulative")
    s.print_stats()

def analyze ():
    global searching, nodes, movesearches
    searching = True
    start = time()
    searchLock.acquire()
    board = history[-1]
    for depth in range (1, 5):
        if not searching: break
        t = time()
        mvs, scr = alphaBeta (table, board, depth, -maxint, maxint)
        
        tempboard = board
        smvs = []
        
        for move in mvs:
            smvs.append(toAN (tempboard, move))
            tempboard = tempboard.move(move)
        smvs = " ".join(smvs)
        
        print depth,"\t", "%0.2f" % (time()-start),"\t", scr,"\t", nodes,"\t", smvs
        print "%0.1f moves/position; %0.1f n/s" % (nodes/float(movesearches), nodes/(time()-t))
        nodes = 0
        movesearches = 0
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
            for depth in range(1,sd+1):
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
    if not line.strip(): continue
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
        analyze()
        #thread.start_new(analyze,())
        
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

#!/usr/bin/python

import gettext
from pychess.System.prefix import addDataPrefix
gettext.install("pychess", localedir=addDataPrefix("lang"), unicode=1)

from time import time
import sys, os
from threading import Lock
from Queue import Queue

from Engine import Engine

from pychess.System.ThreadPool import pool
from pychess.Utils.book import getOpenings
from pychess.Utils.const import *
from pychess.Utils.lutils.lsearch import alphaBeta
from pychess.Utils.lutils import lsearch
from pychess.Utils.lutils.lmove import toSAN, parseAny, parseSAN, FLAG, listToSan
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils import leval
from pychess.Utils.Board import Board

try:
    import psyco
    psyco.bind(alphaBeta)
except ImportError:
    pass

################################################################################
# getBestOpening                                                               #
################################################################################

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

################################################################################
# global variables                                                             #
################################################################################

features = {
    "setboard": 1,
    "analyze": 1,
    "usermove": 1,
    "reuse": 0,
    "draw": 1,
    "sigterm": 1,
    "variants": "normal,nocastle,fischerandom",
    "myname": "PyChess %s" % VERSION
}

sd = 10
skipPruneChance = 0
moves = None
increment = None
mytime = None
#optime = None
forced = False
analyzing = False
scr = 0 # The current predicted score. Used when accepting draw offers
playingAs = WHITE
increment = 0

board = LBoard(NORMALCHESS)
board.applyFen(FEN_START)

################################################################################
# General functions                                                            #
################################################################################

searchLock = Lock()

def stopSearching ():
    lsearch.searching = False
    searchLock.acquire()
    searchLock.release()

def startSearching (searchFunc):
    searchLock.acquire()
    lsearch.searching = True
    def subFunc ():
        searchFunc()
        searchLock.release()
    pool.start(subFunc)

################################################################################
# analyze()                                                                    #
################################################################################

def analyze2 ():
    import profile
    profile.runctx("analyze2()", locals(), globals(), "/tmp/pychessprofile")
    from pstats import Stats
    s = Stats("/tmp/pychessprofile")
    s.sort_stats('cumulative')
    s.print_stats()

def analyze ():
    """ Searches, and prints info from, the position as stated in the cecp
        protocol """
    
    start = time()
    lsearch.endtime = sys.maxint
    
    for depth in xrange (1, 10):
        if not lsearch.searching:
            break
        t = time()
        
        mvs, scr = alphaBeta (board, depth)
        
        smvs = " ".join(listToSan(board, mvs))
        
        print depth, "\t", "%0.2f" % (time()-start), "\t", scr, "\t", \
              lsearch.nodes, "\t", smvs
        
        if lsearch.movesearches:
            print "%0.1f moves/position; %0.1f n/s" % (
                    lsearch.nodes/float(lsearch.movesearches),
                    lsearch.nodes/(time()-t) )
        
        lsearch.nodes = 0
        lsearch.movesearches = 0

################################################################################
# go()                                                                         #
################################################################################

def remainingMovesA (x):
    # Based on regression of a 180k games pgn
    return -1.71086e-12*x**6 \
           +1.69103e-9*x**5 \
           -6.00801e-7*x**4 \
           +8.17741e-5*x**3 \
           +2.91858e-4*x**2 \
           -0.94497*x \
           +78.8979

def remainingMovesB (x):
    # We bet a game will be around 80 moves
    return max(80-x,4)

def go ():
    """ Finds and prints the best move from the current position """
    
    # TODO: Length info should be put in the book.
    # Btw. 10 is not enough. Try 20
    if len(board.history) < 14:
        movestr = getBestOpening(board)
        if movestr:
            mvs = [parseSAN(board, movestr)]
    
    if len(board.history) >= 14 or not movestr:
        
        global mytime, increment, scr
        lsearch.skipPruneChance = skipPruneChance
        lsearch.searching = True
        
        if mytime == None:
            lsearch.endtime = sys.maxint
            print "Searching to depth %d without timelimit" % sd
            mvs, scr = alphaBeta (board, sd)
        
        else:
            usetime = mytime / remainingMovesA(len(board.history))
            if mytime < 6*60+increment*40:
                # If game is blitz, we assume 40 moves rather than 80
                usetime *= 2
            # The increment is a constant. We'll use this allways
            usetime += increment
            if usetime < 0.5:
                # We don't wan't to search for e.g. 0 secs
                usetime = 0.5
            
            starttime = time()
            lsearch.endtime = starttime + usetime
            prevtime = 0
            print "Time left: %3.2f seconds; Planing to thinking for %3.2f seconds" % \
                   (mytime, usetime)
            for depth in range(1, sd+1):
                # Heuristic time saving
                # Don't waste time, if the estimated isn't enough to complete next depth
                if usetime > prevtime*4 or usetime <= 1:
                    lsearch.timecheck_counter = lsearch.TIMECHECK_FREQ
                    search_result = alphaBeta(board, depth)
                    if lsearch.searching:
                        mvs, scr = search_result
                        if time() > lsearch.endtime:
                            # Endtime occured after depth
                            print "Endtime occured after depth"
                            break
                        print "got moves", " ".join(listToSan(board, mvs)), "from depth", depth
                    else:
                        # We were interrupted
                        print "I was interrupted (%d) while searching depth %d" % (lsearch.last, depth)
                        if depth == 1:
                            print "I've got to have some move, so I use what we got"
                            mvs, scr = search_result
                        break
                    prevtime = time()-starttime - prevtime
                else:
                    print "I don't have enough time to go into depth %d" % depth
                    # Not enough time for depth
                    break
            else:
                print "I searched through depths [1, %d]" % (sd+1)
            
            mytime -= time() - starttime
            mytime += increment
        
        if not mvs:
            if not lsearch.searching:
                # We were interupted
                lsearch.movesearches = 0
                lsearch.nodes = 0
                searchLock.release()
                return
            
            #if lsearch.last == 4:
            #    print "resign"
            #else:
            if scr == 0:
                print "result", reprResult[DRAW]
            elif scr < 0:
                if board.color == WHITE:
                    print "result", reprResult[BLACKWON]
                else: print "result", reprResult[WHITEWON]
            else:
                if board.color == WHITE:
                    print "result", reprResult[WHITEWON]
                else: print "result", reprResult[BLACKWON]
            print "last:", lsearch.last, scr
            return
        
        print "moves were:", " ".join(listToSan(board, mvs)), scr
        
        lsearch.movesearches = 0
        lsearch.nodes = 0
        lsearch.searching = False
    
    move = mvs[0]
    print "move", toSAN(board, move)
    board.applyMove(move)
    

################################################################################
# Read raw_input()                                                             #
################################################################################

while True:
    line = raw_input()
    if not line.strip(): continue
    lines = line.split()
    
    if lines[0] == "protover":
        stringPairs = ["=".join([k,repr(v)]) for k,v in features.iteritems()]
        print "feature %s done=1" % " ".join(stringPairs)
    
    elif lines[0] == "usermove":
        
        stopSearching()
        #lsearch.table.clear()
        
        move = parseAny (board, lines[1])
        board.applyMove(move)
        
        playingAs = board.color
        
        if not forced and not analyzing:
            startSearching(go)
        
        if analyzing:
            startSearching(analyze)
    
    elif lines[0] == "sd":
        sd = int(lines[1])
        skipPruneChance = max(0, (5-sd)*0.02)
        if sd >= 5:
            print "If the game has no timesettings, you probably don't want\n"+\
                  "to set a search depth much greater than 4"
    
    elif lines[0] == "level":
        moves = int(lines[1])
        increment = int(lines[3])
        minutes = lines[2].split(":")
        mytime = int(minutes[0])*60
        if len(minutes) > 1:
            mytime += int(minutes[1])
        print "Playing %d moves in %d seconds + %d increment" % \
                (moves, mytime, increment)
    
    elif lines[0] == "time":
        mytime = int(lines[1])/100.
    
    #elif lines[0] == "otim":
    #   optime = int(lines[1])
    
    elif lines[0] == "quit":
        sys.exit()
    
    elif lines[0] == "result":
        # We don't really care what the result is atm.
        sys.exit()
    
    elif lines[0] == "force":
        if not forced and not analyzing:
            forced = True
            stopSearching()
    
    elif lines[0] == "go":
        playingAs = board.color
        forced = False
        startSearching(go)
    
    elif lines[0] == "undo":
        stopSearching()
        board.popMove()
        if analyzing:
            startSearching(analyze)
    
    elif lines[0] == "?":
        stopSearching()
    
    elif lines[0] in ("black", "white"):
        newColor = lines[0] == "black" and BLACK or WHITE
        if playingAs != newColor:
            stopSearching()
            playingAs = newColor
            # It is dangerous to use the same table, when we change color
            #lsearch.table.clear()
            board.setColor(newColor)
            # Concider the case:
            # * White moves a pawn and creates a enpassant cord
            # * Spy analyzer is not set back to white to analyze the
            #   position. An attackable enpassant cord now no longer makes
            #   sense.
            # * Notice though, that when the color is shifted back to black
            #   to make the actual move - and it is an enpassant move - the
            #   cord won't be set in the lboard.
            board.setEnpassant(None)
            if analyzing:
                startSearching(analyze)
    
    elif lines[0] == "analyze":
        playingAs = board.color
        analyzing = True
        startSearching(analyze)
        
    elif lines[0] == "draw":
        if scr <= 0:
            print "offer draw"
        
    elif lines[0] == "random":
        leval.random = True
    
    elif lines[0] == "variant":
        if lines[1] == "fischerandom":
            board.variant = FISCHERRANDOMCHESS
        
    elif lines[0] == "setboard":
        lsearch.searching = False
        stopSearching()
        board.applyFen(" ".join(lines[1:]))
        if analyzing:
            startSearching(analyze)
    
    elif lines[0] in ("xboard", "otim", "hard", "easy", "nopost", "post"):
        pass
    
    else: print "Warning (unknown command):", line

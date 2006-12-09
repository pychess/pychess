#!/usr/bin/python

from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE, TYPE_PYOBJECT
from time import time
import sys, os
import thread

from Engine import Engine
from pychess.Utils.History import hisPool
from pychess.Utils.Move import movePool, parseSAN, parseAN, toAN
from pychess.Utils import eval
from pychess.Utils.const import *
from pychess.Utils.book import getOpenings
from pychess.Utils.validator import findMoves2, isCheck
from pychess.Utils.History import History
from pychess.System.ThreadPool import pool
from pychess.System.LimitedDict import LimitedDict

#from pychess.Savers import epd
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

last = 0

def alphaBeta (table, board, depth, alpha, beta, capture=False):
    global last
    foundPv = False
    amove = []
    
    if table.has_key(board):
        last = -1; return table[board]
    
    if (depth <= 0 and not capture) or depth < -2:
        last = 1; return [], eval.evaluateComplete(board, board.color)
    
    move = None
    for move in findMoves2(board):
        if depth == 2: print move
        
        # TODO: We could use some sort of moveordering here, to make alphaBeta
        # more efficient. The killer move method might be applyable
        
        # If we do order the moves, it will require that we find all moves of
        # the board, instead of only iterating. If we do that, we might also be
        # able to use the validator status function, to test for draws. It'll
        # only require a history object... (treefold)
        
        # The question is wheter it would require much more generating...
        
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
            table[board] = ([move]+mvs, beta)
            last = 3; return [move]+mvs, beta

        if val > alpha:
            map(movePool.add, amove)
            alpha = val
            amove = [move]+mvs
            foundPv = True
        else:
            map(movePool.add, mvs)
    
    if amove: last = 4; result = (amove, alpha)
    elif not move:
        # If not moves were found, this must be a mate or stalemate
        lastn = 5
        if isCheck (board, board.color):
            result = ([], -9999)
        else: result = ([], 0)
    else:
        # If not move made it through alphabeta (should not be possible)
        # We simply pick the last the best, whith th lowest score...
        last = 6; result = ([move], alpha)
    table[board] = result
    return result

sd = 1
moves = 0
seconds = 0
increment = 0
forced = False

history = History()
transpositionTable = LimitedDict(5000)

features = {
    "setboard": 1,
    "analyze": 1,
    "usermove": 1,
    "reuse": 0,
    "draw": 1,
    "myname": "PyChess %s" % VERSION
}

def go ():
    # TODO: Must be threaded. Python threading is ok
    
    # TODO: Length info should be put in the book
    if len(history) < 10:
        movestr = getBestOpening(history[-1])
        if movestr:
            move = parseSAN(history[-1], movestr)
        
    if len(history) >= 10 or not movestr:
        mvs, scr = alphaBeta (transpositionTable, history[-1], sd, -9999, 9999)
        move = mvs[0]
        print "moves were", mvs, "color is", history[-1].color, history.curCol()
        print "last", last
    
    history.add(move, mvlist=False)
    print "move", toAN(history[-2], move)

while True:
    line = raw_input()
    lines = line.split()
    
    if lines[0] == "protover":
        print "feature %s done=1" % \
            " ".join(["=".join([k,repr(v)]) for k,v in features.iteritems()])
    
    elif lines[0] == "usermove":
        
        try:
            move = parseAN (history[-1], lines[1])
        except ParsingError:
            print "Illegal move:", repr(lines[1])
            sys.exit(os.EX_PROTOCOL)
            
        history.add(move, mvlist=False)
        
        thread.start_new(go,())
    
    elif lines[0] == "sd" and lines[1].isdigit():
        sd = int(lines[1])
        if sd < 4: sd = 1
        if 4 <= sd <= 7: sd = 2
        if 7 < sd: sd = 3
        
    elif lines[0] == "level" and len(lines) == 4 and \
            [s.isdigit() for s in lines[1:]] == [True,True,True]:
        moves, seconds, increment = map(int, liens[1:])
        
    elif lines[0] == "quit":
        sys.exit()
    
    elif lines[0] == "force":
        forced = not forced
        
    elif lines[0] == "go":
        thread.start_new(go,())
        
    elif lines[0] == "black":
        pass
    elif lines[0] == "white":
        pass
    
    elif lines[0] == "draw":
        print "offer draw"
    
    elif lines[0] == "setboard":
        io = StringIO()
        io.write(lines[1]+"\n")
        io.seek(0)
        epdfile = epd.load(io)
        io.close()
        history = epdfile.loadToHistory(0,-1)
    
    else: print "Illegal move", line

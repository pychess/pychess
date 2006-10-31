from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE, TYPE_PYOBJECT
from time import time
from threading import Lock

from Engine import Engine
from Utils.History import hisPool
from Utils.Move import movePool, parseSAN
from Utils import eval
from Utils.book import getOpenings
from Utils.validator import findMoves2
from System.ThreadPool import pool

import random
def getBestOpening (history):
    score = 0
    move = None
    for m, w, d, l in getOpenings(history):
        s = (w+d/3.0)*random.random()
        if not move or s > score:
            move = m
            score = s
    return move
    
VERSION = "0.4"

#TODO: Move PyChessEngine to another Process to set its priority

class PyChessEngine (Engine):
    __gsignals__ = {
        'analyze': (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
        'draw_offer': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'resign': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'dead': (SIGNAL_RUN_FIRST, TYPE_NONE, ())
    }

    def __init__ (self, executable, color):
        GObject.__init__(self)
        
        self.color = color
        self.depth = 2
        self.secs = 0
        self.gain = 0
        
        self.analyzing = False
        self.analyzingBoard = 1
        self.analyzeLock = Lock()
        self.analyzeMoves = []
        
        self.alive = True
        
    def makeMove (self, history):
    
        if self.analyzing:
            self.analyzingBoard = len(history)
            pool.start(self.runAnalyze, history)
            return None
            
        omove = getBestOpening(history)
        if omove: return parseSAN(history,omove)

        if self.secs <= 0:
            mvs, score = alphaBeta(self, history, self.depth, -9999, 9999)
        else:
            usetime = self.secs/30+self.gain
            endtime = time() + usetime
            for d in range(self.depth):
                mvs, score = alphaBeta(self, history, d+1, -9999, 9999)
                if time() > endtime:
                    break

        return mvs[0]
    
    def offerDraw (self):
        pass #TODO
    
    def setBoard (self, history):
        pass #No code is needed here
    
    def setStrength (self, strength):
        if strength == 0:
            self.depth = 1
        elif strength == 1:
            self.depth = 2
        elif strength == 2:
            self.depth = 3
    
    def setTime (self, secs, gain):
        self.secs = secs
        self.gain = gain
    
    def canAnalyze (self):
        return True
    
    def analyze (self):
        self.analyzing = True
        self.analyzingBoard = 1
        pool.start(self.runAnalyze, hisPool.pop())
    
    def runAnalyze (self, history):
        self.analyzeLock.acquire()
        del self.analyzeMoves[:]
        his2 = history.clone()
        mvs, score = alphaBeta(self, his2, 1, -9999, 9999)
        self.analyzeMoves = mvs
        if mvs:
            self.emit("analyze", mvs)
        # TODO: When PyChess is put in its own process,
        # this should be turned into a loop, seaking deeper and deeper
        if len(history) == self.analyzingBoard:
            mvs, score = alphaBeta(self, his2, 2, -9999, 9999)
            self.analyzeMoves = mvs
            if mvs:
                self.emit("analyze", mvs)
        self.analyzeLock.release()
        
    def __repr__ (self):
        return "PyChess %s" % VERSION
    
    def __kill__ (self):
        self.alive = False
    
def moves (history):
    #if history.movelist[-1] == None:
    for m in findMoves2(history):
        yield m
    #else:
    #    for cord0, cord1s in history.movelist[-1].iteritems():
    #        for cord1 in cord1s:
    #            try:
    #                yield movePool.pop(history,cord0,cord1)
    #            except:
    #                pass

def alphaBeta (engine, history, depth, alpha, beta):
    
    foundPv = False
    amove = []

    if depth <= 0:
        return [], eval.evaluateComplete(history, history.curCol())
    if not engine.alive:
        return [], 0
    
    move = None
    # TODO: Could this stuff be hashed,
    # so pychess always new what to do in a certain position?
    # TODO: No kind of endgame test
    for move in moves(history):
        his2 = history.clone()
        his2.add(move, mvlist=False)
        
        if foundPv:
            mvs, val = alphaBeta(engine, his2, depth-1, -alpha-1, -alpha)
            val = -val
            if val > alpha and val < beta:
                map(movePool.add, mvs)
                mvs, val = alphaBeta(engine, his2, depth-1, -beta, -alpha)
                val = -val
        else:
            mvs, val = alphaBeta(engine, his2, depth-1, -beta, -alpha)
            val = -val
        
        hisPool.add(his2)
        
        if val >= beta:
            return [move]+mvs, beta

        if val > alpha:
            map(movePool.add, amove)
            alpha = val
            amove = [move]+mvs
            foundPv = True
        else:
            map(movePool.add, mvs)

    if amove: return amove, alpha
    if not move: return [], alpha
    return [move], alpha

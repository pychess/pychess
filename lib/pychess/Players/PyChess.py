from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE, TYPE_PYOBJECT
from time import time
from threading import Lock

from Engine import Engine
from pychess.Utils.History import hisPool
from pychess.Utils.Move import movePool, parseSAN
from pychess.Utils import eval
from pychess.Utils.const import *
from pychess.Utils.book import getOpenings
from pychess.Utils.validator import findMoves2
from pychess.System.ThreadPool import pool
from pychess.System.LimitedDict import LimitedDict

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

#TODO: Move PyChessEngine to another Process to set its priority

class PyChessEngine (Engine):
    __gsignals__ = {
        'analyze': (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
        'draw_offer': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'resign': (SIGNAL_RUN_FIRST, TYPE_NONE, ())
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
        
        self.transpositionTable = LimitedDict(5000)
        
        self.alive = True
        
    def makeMove (self, history):
    
        if self.analyzing:
            self.analyzingBoard = len(history)
            pool.start(self.runAnalyze, history)
            return None
            
        #omove = getBestOpening(history[-1])
        #if omove: return parseSAN(history[-1],omove)

        if self.secs <= 0:
            mvs, score = alphaBeta( self, self.transpositionTable,
                                    history[-1], self.depth, -9999, 9999)
            global last
            if not history[-1][mvs[0].cord0] or \
                    history[-1][mvs[0].cord0].color != self.color:
                raise Exception, "Tried to make illigal move. %s %s %d" % (str(mvs),str(history[-1]), last)
        else:
            usetime = self.secs/30+self.gain
            endtime = time() + usetime
            for d in range(self.depth):
                mvs, score = alphaBeta( self, self.transpositionTable,
                                        history[-1], d+1, -9999, 9999)
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
    
    def setDepth (self, depth):
        self.depth = depth
    
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
        
        mvs, score = alphaBeta( self, self.transpositionTable,
                                history[-1], 1, -9999, 9999)
        self.analyzeMoves = mvs
        if mvs:
            self.emit("analyze", mvs)
        # TODO: When PyChess is put in its own process,
        # this should be turned into a loop, seaking deeper and deeper
        if len(history) == self.analyzingBoard:
            mvs, score = alphaBeta( self, self.transpositionTable,
                                    history[-1], 2, -9999, 9999)
            self.analyzeMoves = mvs
            if mvs:
                self.emit("analyze", mvs)
        self.analyzeLock.release()
        
    def __repr__ (self):
        return "PyChess %s" % VERSION
    
    def __kill__ (self):
        self.alive = False

last = 0

def alphaBeta (engine, table, board, depth, alpha, beta, capture=False):
    global last
    foundPv = False
    amove = []
    
    if table.has_key(board):
        last = -1; return table[board]
    
    if depth <= 0 and not capture:
        last = 1; return [], eval.evaluateComplete(board, board.color)
    if not engine.alive:
        last = 2; return [], 0
    
    move = None
    for move in findMoves2(board):
        try:
            board2 = board.move(move)
        except AttributeError:
            print board, move
            raise
        
        assert depth < 5
        if depth < 5 and board[move.cord1] != None:
            tempcapture = True
        else: tempcapture = False
        
        if foundPv:
            mvs, val = alphaBeta ( engine, table, board2, depth-1,
                                   -alpha-1, -alpha, tempcapture)
            val = -val
            if val > alpha and val < beta:
                map(movePool.add, mvs)
                mvs, val = alphaBeta ( engine, table, board2, depth-1,
                                       -beta, -alpha, tempcapture)
                val = -val
        else:
            mvs, val = alphaBeta ( engine, table, board2, depth-1,
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
    elif not move: last = 5; result = ([], alpha)
    else: last = 6; result = ([move], alpha)
    table[board] = result
    return result

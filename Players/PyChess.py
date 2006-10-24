from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE, TYPE_PYOBJECT

from Engine import Engine
from Utils.History import hisPool
from Utils.Move import movePool
from Utils import eval
from Utils.book import getOpenings
from Utils.validator import findMoves2

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
    
VERSION = "0.1"

class PyChessEngine (Engine):
    __gsignals__ = {
        'draw_offer': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'resign': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'dead': (SIGNAL_RUN_FIRST, TYPE_NONE, ())
    }

    def __init__ (self, executable, color):
        GObject.__init__(self)
        self.color = color
        
    def makeMove (self, history):
        omove = getBestOpening(history)
        if omove: return movePool.pop(history,omove)
        from time import time
        t = time()
        move, score = alphaBeta(history, 2, -9999, 9999)
        print time()-t
        print move, "Score:", score
        print "---"
        return move
    
    def setBoard (self, history):
        pass #No code is needed here
    
    def setStrength (self, strength):
        pass
    
    def setTime (self, secs, gain):
        pass
    
    def __repr__ (self):
        return "PyChess %s" % VERSION

def moves (history):
    if history.movelist[-1] == None:
        for m in findMoves2(history):
            yield m
    else:
        for cord0, cord1s in history.movelist[-1].iteritems():
            for cord1 in cord1s:
                yield movePool.pop(history,(cord0,cord1))

#TODO: RESIGN:
# And now, if the best we can do is ALPHABETA_GIVEUP or worse, then it is
# time to resign...  Unless the opponent was kind wnough to put us in
# stalemate!

#TODO: Add mating support
#TODO: Add hash support
def alphaBeta (history, depth, alpha, beta):
    foundPv = False

    amove = None

    if depth <= 0:
        return None, eval.evaluateComplete(history, history.curCol())
    
    #his2 = history.clone()
    #his2.moves.append(None)
    #his2.boards.append(his2.boards[-1])
    #m, val = alphaBeta(his2, depth-2, -beta, -beta+1)
    #if m: movePool.add(m)
    #val = -val
    #if val >= beta:
    #    return None, beta
    #hisPool.add(his2)
    
    for move in moves(history):
        his2 = history.clone()
        his2.add(move, mvlist=False)
        
        if foundPv:
            m, val = alphaBeta(his2, depth-1, -alpha-1, -alpha)
            if m: movePool.add(m)
            val = -val
            if val > alpha and val < beta:
                m, val = alphaBeta(his2, depth-1, -beta, -alpha)
                if m: movePool.add(m)
                val = -val
        else:
            m, val = alphaBeta(his2, depth-1, -beta, -alpha)
            if m: movePool.add(m)
            val = -val
        
        hisPool.add(his2)
        
        if val >= beta:
            return move, beta

        if val > alpha:
            alpha = val
            amove = move
            foundPv = True

    if amove: return amove, alpha
    return move, alpha

from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE, TYPE_PYOBJECT

from Engine import Engine
from Utils.History import hisPool
from Utils.Move import movePool
from Utils import eval
from Utils.book import getOpenings

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
        startscore = eval.evaluateComplete(history, self.color)
        print "start", startscore
        move, score = self.oneMoreLevel(history, startscore, 2, 0)
        print move,"SCORE",score
        return move
    
    def oneMoreLevel (self, history, lastScore, levels, current):
        #worse = []
        #best = []
        best = None
        score = -9999
        last = levels -1 == current
        
        omove = getBestOpening(history)
        if omove:
            return movePool.pop(history,omove), 2000
        
        for move in self.moves(history):
            his2 = history.clone()
            his2.add(move, mvlist=not last)
            s = eval.evaluateComplete(his2, self.color)
            if current % 2 == 1: s = -s
            #print move, s
            
            if not last:
                m2, s2 = self.oneMoreLevel (his2, s, levels, current+1)
                #print "   ",move, m2, s2
                if not best or s2 > score:
                    if best:
                        movePool.add(best)
                    best = move
                    score = s2
                else: movePool.add(move)
            
            elif s > score:
                best = move
                score = s
            hisPool.add(his2)
        
        if current % 2 == 1: score = -score
        return best,score
        
    def moves (self, history):
        if history.movelist[-1] == None:
            history.movelist[-1] = validator.findMoves(history)
        for cord0, cord1s in history.movelist[-1].iteritems():
            for cord1 in cord1s:
                yield movePool.pop(history,(cord0,cord1))
    
    def setStrength (self, strength):
        pass
    
    def setTime (self, secs, gain):
        pass
    
    def __repr__ (self):
        return "PyChess %s" % VERSION

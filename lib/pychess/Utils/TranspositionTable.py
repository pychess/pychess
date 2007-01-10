from UserDict import UserDict
from const import hashfALPHA, hashfBETA, hashfEXACT
from pychess.System.LimitedDict import LimitedDict
from pychess.Utils.Move import Move

class TranspositionTable (UserDict):
    def __init__ (self, maxSize):
        UserDict.__init__(self)
        assert maxSize > 0
        self.maxSize = maxSize
        self.krono = []
        self.maxdepth = 0
        
        self.cutters = LimitedDict(100)
        
    def __setitem__ (self, key, item):
        if not key in self:
            if len(self) >= self.maxSize:
                try:
                    del self[self.krono[0]]
                except KeyError: pass # Overwritten
                del self.krono[0]
        self.data[key] = item
        self.krono.append(key)
    
    def probe (self, board, depth, alpha, beta):
        if not board in self: return
        entries = self[board]
        for d in xrange(self.maxdepth, depth-1, -1):
            if not d in entries: continue
            recboard, moves, score, hashf = entries[d]
            if not (board == recboard):
                print "NOT (board == recboard)"
                continue
            if hashf == hashfEXACT:
                return moves, score
            if hashf == hashfALPHA and score <= alpha:
                return moves, alpha
            if hashf == hashfBETA and score >= beta:
                return moves, beta
            return
    
    def record (self, board, moves, depth, score, hashf):
        if board in self:
            self[board][depth] = (board, moves, score, hashf)
        else: self[board] = {depth:(board, moves, score, hashf)}
        if depth > self.maxdepth: self.maxdepth = depth
    
    def addBetaCutter (self, color, cords):
        key = (color, cords)
        if not key in self.cutters:
            self.cutters [key] = 1
        else: self.cutters [key] += 1
    
    def moveCmp (self, key1, key2):
        key1in = key1 in self.cutters
        key2in = key2 in self.cutters
        if not key1in and not key2in:
            return 0
        if key1in and not key2in:
            return 1
        if not key1in and key2in:
            return -1
        return self.cutters[key1] - self.cutters[key2]
    
    def sortMoves (self, moves, color):
        list = [(color,move.cords) for move in moves]
        list.sort(self.moveCmp)
        return [Move(*cords) for color,cords in list]

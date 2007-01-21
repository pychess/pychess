from UserDict import UserDict
from pychess.Utils.const import hashfALPHA, hashfBETA, hashfEXACT, WHITE
from pychess.System.LimitedDict import LimitedDict
from pychess.Utils.Move import Move

class TranspositionTable (UserDict):
    def __init__ (self, maxSize):
        UserDict.__init__(self)
        assert maxSize > 0
        self.maxSize = maxSize
        self.krono = []
        self.maxdepth = 0
        
        self.killer1 = [-1]*20
        self.killer2 = [-1]*20
        self.hashmove = [-1]*20
        
    def __setitem__ (self, key, item):
        if not key in self:
            if len(self) >= self.maxSize:
                try:
                    del self[self.krono[0]]
                except KeyError: pass # Overwritten
                del self.krono[0]
        self.data[key] = item
        self.krono.append(key)
    
    def probe (self, hash, depth, alpha, beta):
        if not hash in self: return
        move, score, hashf = self[hash]
        if hashf == hashfEXACT:
            return move, score, hashf
        if hashf == hashfALPHA and score <= alpha:
            return move, alpha, hashf
        if hashf == hashfBETA and score >= beta:
            return move, beta, hashf
    
    def record (self, hash, move, score, hashf):
        self[hash] = (move, score, hashf)
    
    def addKiller (self, ply, move):
        if self.killer1[ply] == -1:
            self.killer1[ply] = move
        elif move != self.killer1[ply]:
            self.killer2[ply] = move
    
    def isKiller (self, ply, move):
        if self.killer1[ply] == move or self.killer2[ply] == move:
            return True
        if ply > 0 and (self.killer1[ply-1] == move or \
                        self.killer2[ply-1] == move):
            return True
        return False
    
    def setHashMove (self, ply, move):
        self.hashmove[ply] = move
    
    def isHashMove (self, ply, move):
        return self.hashmove[ply] == move

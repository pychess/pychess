import sys, os, atexit

from Utils.Log import LogPipe
from Utils.Log import log
from Engine import Engine

class Crafty (Engine):
    
    name = None
    def __init__ (self):
        from popen2 import popen4
        self.inn, self.out = popen4("nice crafty", 0)
        self.out = LogPipe(self.out, "CrW: ")
        atexit.register(self.__del__)
        
        print >> self.out, "xboard"
        for line in self._get():
            if line.startswith("Crafty "):
                self.name = line
        
    def setStrength (self, strength):
        if strength == 0:
            print >> self.out, "easy"
            print >> self.out, "random"
            print >> self.out, "book width 100"
            print >> self.out, "sd 1"
        elif strength == 1:
            print >> self.out, "easy"
            print >> self.out, "random"
            print >> self.out, "book width 10"
            print >> self.out, "sd 4"
        elif strength == 2:
            print >> self.out, "hard"
            print >> self.out, "book width 3"
            print >> self.out, "sd 9"
            print >> self.out, "egtb"
    
    def setTime (self, secs, gain):
        print >> self.out, "level 0", secs/60.0, gain
            
    def makeMove (self, history):
        from Utils.Move import Move
        if len(history.moves) < 1:
            print >> self.out, "go"
        else:
            move = history.moves[-1]
            print >> self.out, str(move)
        
        replies = self._get()
        for reply in replies:
            if reply.startswith("move "):
                mymove = reply[5:].strip()
                return Move(history, mymove)
                
        log.error("Unable to parse crafty reply '%s'" % str(replies))
        print history[-1]
        return None
    
    # Methods usable in human vs. human enviroments
    
    def score (self):
        pass
    
    def getSpeed (self):
        pass
    
    def hint (self):
        pass
    
    def book (self):
        pass
    
    # Private methods
    
    def _get (self):
        print >> self.out, "flush plz"
        result = []
        while True:
            line = self.inn.readline()
            log.debug("CrR: " + line.strip())
            if line == "Illegal move: flush\n":
                break
            result += [line]
        return result
    
    
    # Other methods
    
    def testEngine (self):
        assert repr(self), "You must have crafty installed"
    
    def __repr__ (self):
        return self.name
    
    def __del__ (self):
        print >> self.out, "end"
        

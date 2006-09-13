import sys, os, atexit

from Utils.Log import LogPipe
from Utils.Log import log
from Engine import Engine, EngineDead

class GnuChess (Engine):
    
    def __init__ (self):
        from popen2 import Popen4
        popen = Popen4("nice gnuchess -x", 0)
        self.out, self.inn = popen.tochild, popen.fromchild
        self.out = LogPipe(self.out, "GnW: ")
        self.pid = popen.pid
        atexit.register(self.__del__)
        self._get()
        
    def setStrength (self, strength):
        if strength == 0:
            print >> self.out, "easy"
            print >> self.out, "random"
            print >> self.out, "book random"
            print >> self.out, "depth 1"
        elif strength == 1:
            print >> self.out, "easy"
            print >> self.out, "random"
            print >> self.out, "book random"
            print >> self.out, "depth 4"
        elif strength == 2:
            print >> self.out, "hard"
            print >> self.out, "book best"
            print >> self.out, "depth 9"
    
    def setTime (self, secs, gain):
        print >> self.out, "level 0", secs/60.0, gain
            
    def makeMove (self, history):
        from Utils.Move import Move
        if len(history.moves) < 1:
            print >> self.out, "go"
        else:
            move = history.moves[-1]
            print >> self.out, move.gnuchess(history[-2])
        
        replies = self._get()
        for reply in replies:
            if reply.startswith("My move is"):
                mymove = reply[12:].strip()
                c1, c2 = mymove[:2], mymove[2:4]
                if len(mymove) == 5:
                    return Move(history, (c1, c2), mymove[4:5])
                return Move(history, (c1, c2))
                
        log.error("Unable to parse gnuchess reply '%s'" % str(replies))
        print history[-1]
        return None
    
    # Methods usable in human vs. human enviroments
    
    def score (self):
        print >> self.out, "show pin"
        reply = self._get()
        return int(reply[-1][24:])
    
    def getSpeed (self):
        print >> self.out, "test movegenspeed"
        reply = self._get()
        e = reply[-1].find(".")
        return int(reply[-1][7:e])
    
    def hint (self):
        print >> self.out, "hint"
        return _get()[0][6:]
    
    from re import compile
    bookExpr = compile(r"(\w{2,3})\((\d+)?/?(\d+)?/?(\d+)?/?(\d+)?\)")
    def book (self):
        """[(move,percent,wins,loses,draws),]"""
        print >> self.out, "bk"
        reply = self._get()
        if len(reply) < 2 or reply[1].endswith("there is no move"):
            return []
        return self.bookExpr.findall("".join(reply))
    
    # Private methods
    
    def _get (self):
        print >> self.out, "flush plz"
        result = []
        while True:
            line = self.inn.readline()
            if not line.strip():
                raise EngineDead
            if line == "Illegal move: flush plz\n":
                break
            if line.find("Illegal move") >= 0:
                log.error("GnR: " + line.strip())
            else: log.debug("GnR: " + line.strip())
            result += [line]
        return result
    
    # Other methods
    
    def testEngine (self):
        return repr(self) and True or False
    
    def showBoard (self):
        """Mostly for debugging"""
        print >> self.out, "show board"
        log.log("".join(self._get()))
    
    def __repr__ (self):
        from os import popen
        if not hasattr(self,"name"):
            self.name = popen("gnuchess --version").read()[:-1]
        return self.name
    
    def __del__ (self):
        os.system("kill %d" % self.pid)

if __name__ == "__main__":
    c = GnuChess()
    c.move
    del c

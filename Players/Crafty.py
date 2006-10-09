import sys, os, atexit
from gobject import GObject

from System.Log import LogPipe
from System.Log import log
from Engine import Engine, EngineDead

class Crafty (Engine):
    
    def __init__ (self):
        GObject.__init__(self)
        
        self.last = "notnull"
        self.name = ""
        
        from popen2 import Popen4
        popen = Popen4("nice crafty", 0)
        self.out, self.inn = popen.tochild, popen.fromchild
        self.out = LogPipe(self.out, "CrW: ")
        self.pid = popen.pid
        atexit.register(self.__del__)
        
        print >> self.out, "xboard"
        try:
            print >> self.out, "info"
            for line in self._get("Crafty"):
                if line.startswith("Crafty "):
                    self.name = line
            # Crafty sets a \n after his name, and this is not needed
            if self.name[len(self.name)-1] == '\n':
                self.name = self.name[0:len(self.name)-1]
        except:
            self.name = "Crafty"
        
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
            print >> self.out, move.gnuchess(history[-2])
        
        replies = self._get("move ")
        for reply in replies:
            if reply.startswith("move "):
                mymove = reply[5:].strip()
                return Move(history, mymove)
                
        log.error("Unable to parse crafty reply '%s'" % str(replies))
        print history[-1]
        return None
    
    # Private methods
    
    def _get (self, waitfor):
        log.debug("Cr waiting for: '%s'" % waitfor)
        result = []
        while True:
            line = self.inn.readline()
            if not line.strip() and not self.last:
                raise EngineDead
            self.last = line.strip()
            if line.find("Illegal move") >= 0:
                log.error("CrR: " + line.strip())
            else: log.debug("CrR: " + line.strip(), flush=True)
            result += [line]
            if line.find(waitfor) >= 0:
                log.debug("Cr found: '%s' in '%s'" % (waitfor,line))
                break
        return result
    
    def hurry (self):
        print >> self.out, "?"
    
    # Other methods
    
    def showBoard (self):
        """Mostly for debugging"""
        print >> self.out, "display"
        from time import sleep
        sleep(0.1)
        print >> self.out, "ed"
        log.log("".join(self._get("ed")[:-1]))
    
    def __repr__ (self):
        return self.name
    
    def __del__ (self):
        os.system("kill %d" % self.pid)

def testEngine ():
    for path in os.environ["PATH"].split(":"):
        if os.path.isfile(os.path.join(path,"crafty")):
            return True
    return False

import sys, os, atexit

from System.Log import LogPipe
from System.Log import log
from System import Log
import gobject
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, TYPE_PYOBJECT, TYPE_INT
from validator import DRAW, WHITEWON, BLACKWON
from Move import Move
from thread import start_new
from Players.Engine import EngineDead
from Queue import Queue
from threading import Condition
from System.ThreadPool import pool

class Oracle (gobject.GObject):
    
    __gsignals__ = {
        'foretold_move': (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT, TYPE_INT)),
        'foretold_end': (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_INT, TYPE_INT)),
        'clear': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'rmfirst': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'foundbook': (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
        'foundscore': (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_INT,))
    }
    
    def __init__ (self):
        gobject.GObject.__init__(self)
        return
        from popen2 import Popen4
        popen = Popen4("nice gnuchess -x", 0)
        self.out, self.inn = popen.tochild, popen.fromchild
        self.out = LogPipe(self.out, "Ora(Gn)W: ")
        self.pid = popen.pid
        atexit.register(self.__del__)
        
        self.queue = Queue(0)
        self.cond = Condition()
        self.future = []
        
        print >> self.out, "manual"
        print >> self.out, "hard"
    
    def addMove (self, his):
        return
        # FIXME: rmfirst code has been disabled until there is a way
        # to make it emit correct showbook and showscore signals. URGENT!!! 
        
        #if self.future and self.future[0][0] == his.moves[-1]:
        #    del self.future[0]
        #    self.emit("rmfirst")
        #else:
        self.emit("clear")
        #print >> self.out, "depth 1"
        self.queue.put(his.clone())
    
    def reset (self):
        return
        self.running = False
        self.cond.acquire()
        print >> self.out, "new"
        print >> self.out, "manual"
        print >> self.out, "hard"
        self.future = []
        self.bookmv = []
        self.history.reset()
        self.emit("clear")
        self.emit("foundscore", self.score())
        self.emit("foundbook", self.book())
        self.cond.release()
        self.running = True
        self.run()
    
    def game_ended (self):
        return
        self.running = False
        self.cond.acquire()
        print >> self.out, "new"
        print >> self.out, "manual"
        print >> self.out, "hard"
        self.future = []
        self.bookmv = []
        self.emit("foundbook", [])
        self.emit("clear")
        self.cond.release()
    
    def attach (self, history):
        return
        self.history = history.clone()
        history.connect("changed", self.addMove)
        history.connect("cleared", lambda h: pool.start(self.reset))
        history.connect("game_ended", lambda m,s,c: pool.start(self.game_ended))
        
    # Private methods
    
    def _run (self):
        return
        dead = False
        while self.running:
            self.cond.acquire()
            while True:
                try: history = self.queue.get(block=dead)
                except: break
                self._writemove(history)
                dead = False
            #print >> self.out, "depth %d" % max(min(len(self.future),6),2)
            print >> self.out, "go"
            if not self._getmove():
                dead = True
            self.cond.release()
    
    def run (self):
        pool.start(self._run)
    
    def _writemove (self, history):
        for f in self.future:
            print >> self.out, "undo"
        
        if len(history.moves) >= 1:
            move = history.moves[-1]
            print >> self.out, move.gnuchess(history[-2])
            print >> self.out, "manual"
        else: return
        self._get(move.gnuchess(history[-2]), "{draw}", "{computer")
        
        del self.future[:]
        self.history = history
        
        self.emit("foundscore", self.score())
        self.emit("foundbook", self.book())
    
    def _getmove (self):
        for reply in self._get("My move is", "{draw}", "{computer"):
            if reply.startswith("My move is"):
                smove = reply[12:].rstrip()
                c1, c2 = smove[:2], smove[2:4]
                
                try:
                    if len(smove) == 5:
                        move = Move(self.history, (c1, c2), smove[4])
                    else: move = Move(self.history, (c1, c2))
                except:
                    print self.history[-1]
                    break
                
                self.history.add(move)
                score = self.score()
                self.future.append((move,score))
                if self.queue.empty():
                    self.emit("foretold_move", move, score)

            elif reply.find("{draw}") >= 0:
                if self.queue.empty():
                    self.emit("foretold_end", len(self.future), DRAW)
                return False
            elif reply.find("{computer") >= 0:
                if self.queue.empty():
                    self.emit("foretold_end", len(self.future), WHITEWON) #TODO: Put the right player
                return False
        return True
    
    def _get (self, *waitfor):
        print >> self.out, "flush"
        print >> self.out, "manual"
        log.debug("Ora(Gn) waiting for: '%s'" % "' or '".join(waitfor))
        result = []
        while True:
            line = self.inn.readline().strip()
            if len(result) >= 2 and not line.strip() and \
                    not result[-1] and not result[-2]:
                raise EngineDead
            if line.find("Illegal move") >= 0 and not line.find("flush") >= 0:
                log.error("Ora(Gn)R: " + line)
                Log.debug = True
                print >> self.out, "show board"
                print self.history[-1]
            else: log.debug("Ora(Gn)R: " + line)
            result += [line]
            if len([True for p in waitfor if line.find(p) >= 0]) > 0:
                break
        return result
    
    def score (self):
        print >> self.out, "show score"
        for line in self._get("Phase"):
            if line.startswith("Phase"):
                s = line.find("sco")
                score = int(line[s+8:])
                if len(self.history.moves) % 2 == 1:
                    score = -score
                return score
    
    from re import compile
    bookExpr = compile(r"(\w{2,3})\((\d+)?/?(\d+)?/?(\d+)?/?(\d+)?\)")
    def book (self):
        """[(move,percent,wins,loses,draws),]"""
        print >> self.out, "bk"
        print >> self.out, "flush bk"
        reply = self._get("flush bk")
        if len(reply) < 2 or reply[1].endswith("there is no move"):
            return []
        return self.bookExpr.findall("".join(reply))
    
    # Other methods
    
    def testEngine (self):
        return repr(self) and True or False
    
    def __repr__ (self):
        from os import popen
        if not hasattr(self,"name"):
            self.name = popen("gnuchess --version").read()[:-1]
        return "Oracle: "+self.name
    
    def __del__ (self):
        os.system("kill %d" % self.pid)

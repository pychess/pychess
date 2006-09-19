import sys, os, atexit

from System.Log import LogPipe
from System.Log import log
import gobject
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, TYPE_PYOBJECT, TYPE_INT
from validator import STALE, MATE
from Utils.Move import Move
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
        'foundbook': (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,))
    }
    
    def __init__ (self):
        gobject.GObject.__init__(self)
        
        from popen2 import Popen4
        popen = Popen4("nice gnuchess -x", 0)
        self.out, self.inn = popen.tochild, popen.fromchild
        self.out = LogPipe(self.out, "Ora(Gn)W: ")
        self.pid = popen.pid
        atexit.register(self.__del__)
        
        self.queue = Queue(0)
        self.cond = Condition()
        
        print >> self.out, "manual"
        print >> self.out, "hard"
        print >> self.out, "book best"
    
    def addMove (self, his):
        if self.future and self.future[0][0] == his.moves[-1]:
            del self.future[0]
            self.emit("rmfirst")
        else:
            self.emit("clear")
            print >> self.out, "depth 1"
            self.queue.put(his.clone())
    
    def reset (self):
        self.running = False
        self.cond.acquire()
        print >> self.out, "new"
        print >> self.out, "manual"
        print >> self.out, "hard"
        print >> self.out, "book best"
        self.future = []
        self.bookmv = []
        self.history.reset()
        self.emit("clear")
        self.cond.release()
        self.run()
    
    def attach (self, history):
        self.history = history.clone()
        history.connect("changed", self.addMove)
        history.connect("cleared", lambda h: self.reset())
        
    # Private methods
    
    def _run (self):
        self.running = True
        dead = False
        while self.running:
            self.cond.acquire()
            while True:
                try: history = self.queue.get(block=dead)
                except: break
                self._writemove(history)
                dead = False
            print >> self.out, "depth %d" % max(min(len(self.future),6),2)
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
                
                self.history.add(move)
                score = self.score()
                self.future.append((move,score))
                if self.queue.empty():
                    self.emit("foretold_move", move, score)

            elif reply.find("{draw}") >= 0:
                if self.queue.empty():
                    self.emit("foretold_end", len(self.future), STALE)
                return False
            elif reply.find("{computer") >= 0:
                if self.queue.empty():
                    self.emit("foretold_end", len(self.future), MATE)
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
                sys.exit()
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
                return int(line[s+8:])
    
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


import sys, os, time, thread
from threading import Condition, Lock, RLock
from Queue import Queue

from pychess.Players.Player import PlayerIsDead
from pychess.Players.Engine import Engine
from pychess.Utils.Move import Move, parseSAN, parseAN, parseLAN, toSAN, toAN
from pychess.Utils.Cord import Cord
from pychess.Utils.const import *
from pychess.System.Log import log

class ProtocolEngine (Engine):
    
    def __init__ (self, args, color):
        Engine.__init__(self)
        self.proto = args[0] (args[1:], color)
        
        self.readycon = Condition()
        self.runWhenReadyLock = RLock()
        self.readylist = []
        
        self.movequeue = Queue()
        self.analyzeMoves = []
        
        self.proto.connect("draw_offer", lambda p: self.emit("action",DRAW_OFFER,0))
        self.proto.connect("resign", lambda p: self.emit("action",RESIGNATION,0))
        self.proto.connect("move", lambda p, move: self.movequeue.put(move))
        self.proto.connect("dead", lambda p: self.movequeue.put(None))
        self.proto.connect("analyze", self.onAnalyze)
        self.proto.connect("ready", self.onReady)
    
    def setStrength (self, strength):
        self.runWhenReady(self.proto.setStrength, strength)
    
    def runWhenReady (self, method, *args):
        self.runWhenReadyLock.acquire()
        if self.proto.ready:
            method(*args)
        else:
            self.readylist.append((method,args))
        self.runWhenReadyLock.release()
    
    def onReady (self, proto):
        self.readycon.acquire()
        if self.readylist:
            for method, args in self.readylist:
                method(*args)
        self.readycon.notifyAll()
        self.readycon.release()
    
    def setTime (self, secs, gain):
        self.runWhenReady(self.proto.setTimeControls, secs, gain)
    
    def setBoard (self, fen):
        self.runWhenReady(self.proto.setBoard, fen)
    
    def hurry (self):
        self.runWhenReady(self.proto.moveNow)
    
    def offerDraw (self):
        self.runWhenReady(self.proto.offerDraw)
    
    def makeMove (self, gamemodel):
        self.runWhenReady(self.proto.move, gamemodel)
        
        if self.proto.isAnalyzing():
            del self.analyzeMoves[:]
            return
        
        move = self.movequeue.get()
        if not move:
            raise PlayerIsDead
        
        return move
    
    def _wait (self):
        if self.proto.ready:
            return
        self.readycon.acquire()
        while not self.proto.ready and self.proto.connected:
            self.readycon.wait()
        self.readycon.release()
        if not self.proto.connected:
            return False
        return True
    
    def onAnalyze (self, proto, moves):
        # TODO: Sometimes lines may look like:
        # 2. 58 0 1259	 Qxf5 Bh4+ Kd2 exd4
        # 3. 35 0 3791	 Qxf5
        # In these cases we should not skip the more moves
        self.analyzeMoves = moves
        self.emit ("analyze", moves)
    
    def canAnalyze (self):
        self._wait()
        return self.proto.canAnalyze()
    
    def analyze (self, inverse=False):
        self.runWhenReady(self.proto.analyze, inverse)
    
    def updateTime (self, secs, opsecs):
        self.runWhenReady(self.proto.time, secs, opsecs)
    
    def pause (self):
        self.runWhenReady(self.proto.pause)
        
    def resume (self):
        self.runWhenReady(self.proto.resume)
    
    def undoMoves (self, move):
        self.runWhenReady(self.proto.undoMoves, move)
    
    def __repr__ (self):
        self._wait()
        return repr(self.proto)
    
    def end (self, status, reason):
        self.proto.end(status, reason)
    
    def kill (self, reason):
        self.proto.kill(reason)

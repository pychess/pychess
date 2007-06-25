
import sys, os, time, thread
from threading import Condition, Lock, RLock

from pychess.Players.Player import PlayerIsDead
from pychess.Players.Engine import Engine
from pychess.Utils.Move import Move, parseSAN, parseAN, parseLAN, toSAN, toAN
from pychess.Utils.Cord import Cord
from pychess.Utils.Offer import Offer
from pychess.Utils.const import *
from pychess.System.Log import log

class ProtocolEngine (Engine):
    
    def __init__ (self, proto):
        Engine.__init__(self)
        
        self.proto = proto
        self.color = proto.color
        
        self.readycon = Condition()
        self.runWhenReadyLock = RLock()
        self.readylist = []
        
        self.move = None
        self.movecon = Condition()
        self.analyzeMoves = []
        
        self.proto.connect("draw_offer",
                lambda p: self.emit("accept",Offer(DRAW_OFFER)))
        self.proto.connect("resign",
                lambda p: self.emit("offer",Offer(RESIGNATION)))
        self.proto.connect("move", lambda p, move: self._setMove(move))
        self.proto.connect("dead", lambda p: self._setMove("dead"))
        self.proto.connect("analyze", self.onAnalyze)
        self.proto.connect("ready", self.onReady)
    
    def setStrength (self, strength):
        self.runWhenReady(self.proto.setStrength, strength)
    
    def setTime (self, secs, gain):
        self.runWhenReady(self.proto.setTimeControls, secs, gain)
    
    
    def _setMove (self, move):
        self.movecon.acquire()
        self.move = move
        self.movecon.notify()
        self.movecon.release()
    
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
    
    
    def updateTime (self, secs, opsecs):
        self.runWhenReady(self.proto.time, secs, opsecs)
    
    def makeMove (self, gamemodel):
        self.runWhenReady(self.proto.move, gamemodel)
        
        if self.proto.isAnalyzing():
            del self.analyzeMoves[:]
            return
        
        self.movecon.acquire()
        while not self.move:
            self.movecon.wait()
        self.movecon.release()
        
        if self.move == "dead":
            raise PlayerIsDead
        
        move = self.move
        self.move = None
        return move
    
    def offerDraw (self):
        self.runWhenReady(self.proto.offerDraw)
    
    def offerError (self, offer, error):
        # We don't keep track if engine draws are offers or accepts. We just
        # Always assume they are accepts, and if they are not, we get this error
        # and emit offer instead
        if offer.offerType == DRAW_OFFER and \
                error == ACTION_ERROR_NONE_TO_ACCEPT:
            self.emit("offer", Offer(DRAW_OFFER))
    
    
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
    
    
    def setBoard (self, model):
        self.runWhenReady(self.proto.setBoard, model)
    
    def hurry (self):
        self.runWhenReady(self.proto.moveNow)
    
    def pause (self):
        self.runWhenReady(self.proto.pause)
        
    def resume (self):
        self.runWhenReady(self.proto.resume)
    
    def undoMoves (self, moves, gamemodel):
        self.runWhenReady(self.proto.undoMoves, moves, gamemodel)
    
    
    def end (self, status, reason):
        self.proto.end(status, reason)
    
    def kill (self, reason):
        self.proto.kill(reason)
    
    
    def __repr__ (self):
        self._wait()
        return repr(self.proto)

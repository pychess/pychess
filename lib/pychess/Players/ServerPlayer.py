
from Queue import Queue

from Player import Player, PlayerIsDead, TurnInterrupt
from pychess.Utils.Offer import Offer
from pychess.Utils.Move import parseSAN, toAN, ParsingError, listToSan
from pychess.Utils.const import *

class ServerPlayer (Player):
    __type__ = REMOTE
    
    def __init__ (self, gamemodel, name, gameno, color):
        Player.__init__(self)
        
        self.queue = Queue()
        self.okqueue = Queue()
        
        self.name = name
        self.color = color
        self.gameno = gameno
        self.gamemodel = gamemodel
        self.connection = self.gamemodel.connection
        
        self.connection.bm.connect("moveRecieved", self.moveRecieved)
        self.connection.om.connect("onOfferAdd", self.onOfferAdd)
        self.connection.om.connect("onOfferRemove", self.onOfferRemove)
        self.connection.cm.connect("privateMessage", self.onPrivateMessage)
        
        self.offerToIndex = {}
        self.indexToOffer = {}
        self.lastPly = -1
    
    def onOfferAdd (self, om, index, offer):
        self.indexToOffer[index] = offer
        self.emit ("offer", offer)
    
    def onOfferRemove (self, om, index):
        if index in self.indexToOffer:
            self.emit ("withdraw", self.indexToOffer[index])
    
    def onPrivateMessage (self, cm, name, title, isadmin, text):
        if name == self.name:
            self.emit("offer", Offer(CHAT_ACTION, text))
    
    def putMessage (self, text):
        self.connection.cm.tellPlayer (self.name, text)
    
    def offer (self, offer):
        self.connection.om.offer(offer, self.lastPly)
    
    def offerDeclined (self, offer):
        pass
    
    def offerWithdrawn (self, offer):
        pass
    
    def offerError (self, offer, error):
        pass
    
    def moveRecieved (self, bm, moveply, sanmove, gameno, movecol):
        if gameno == self.gameno:
            # We want the current ply rather than the moveply, so we add one
            curply = int(moveply) +1
            # In some cases (like lost on time) the last move is resent
            if curply <= self.lastPly:
                return
            self.lastPly = curply
            if movecol == self.color:
                self.queue.put((self.lastPly,sanmove))
                # Ensure the fics thread doesn't continue parsing, before the
                # game/player thread has recieved the move.
                # Specifically this ensures that we aren't killed due to end of
                # game before our last move is recieved
                self.okqueue.get(block=True)
    
    def makeMove (self, gamemodel):
        self.gamemodel = gamemodel
        self.lastPly = gamemodel.ply
        
        if gamemodel.moves and gamemodel.inControl:
            self.connection.bm.sendMove (
                    toAN (gamemodel.boards[-2], gamemodel.moves[-1]))
        
        item = self.queue.get(block=True)
        try:
            if item == "del":
                raise PlayerIsDead
            if item == "int":
                raise TurnInterrupt
            
            ply, sanmove = item
            if ply < gamemodel.ply:
                # This should only happen in an observed game
                self.emit("offer", Offer(TAKEBACK_FORCE, ply))
            
            try:
                move = parseSAN (gamemodel.boards[-1], sanmove)
            except ParsingError, e:
                e = "%s\n%s" % (e.args[0],
                        listToSan(gamemodel.boards[0], gamemodel.moves))
                raise PlayerIsDead, e
            return move
        finally:
            self.okqueue.put("ok")
    
    def __repr__ (self):
        return self.name
    
    
    def pause (self):
        pass
    
    def resume (self):
        pass
    
    def setBoard (self, fen):
        # setBoard will currently only be called for ServerPlayer when starting
        # to observe some game. In this case FICS already knows how the board
        # should look, and we don't need to set anything
        pass
    
    def end (self, status, reason):
        self.queue.put("del")
    
    def kill (self, reason):
        p = self.gamemodel.players
        if p[0].__type__ != REMOTE or p[1].__type__ != REMOTE:
            self.connection.om.offer(Offer(RESIGNATION), self.lastPly)
        self.queue.put("del")
    
    def undoMoves (self, movecount, gamemodel):
        # If current player has changed so that it is no longer us to move,
        # We raise TurnInterruprt in order to let GameModel continue the game
        if movecount % 2 == 1 and gamemodel.curplayer != self:
            self.queue.put("int")

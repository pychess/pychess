
from Queue import Queue

from Player import Player, PlayerIsDead, TurnInterrupt
from pychess.Utils.Offer import Offer
from pychess.Utils.Move import parseSAN, toSAN, ParsingError, listToSan
from pychess.Utils.const import *

class ServerPlayer (Player):
    __type__ = REMOTE
    
    def __init__ (self, gamemodel, name, external, gameno, color):
        Player.__init__(self)
        
        self.queue = Queue()
        
        self.name = name
        self.color = color
        self.gameno = gameno
        self.gamemodel = gamemodel
        self.connection = self.gamemodel.connection
        
        # If we are not playing against a player on the users computer. E.g.
        # when we observe a game on FICS. In these cases we don't send anything
        # back to the server.
        self.external = external
        
        self.connection.bm.connect("moveRecieved", self.moveRecieved)
        self.connection.om.connect("onOfferAdd", self.onOfferAdd)
        self.connection.om.connect("onOfferRemove", self.onOfferRemove)
        
        self.offerToIndex = {}
        self.indexToOffer = {}
        self.lastPly = -1
    
    def onOfferAdd (self, om, index, offer):
        self.indexToOffer[index] = offer
        self.emit ("offer", offer)
    
    def onOfferRemove (self, om, index):
        if index in self.indexToOffer:
            self.emit ("withdraw", self.indexToOffer[index])
    
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
    
    def makeMove (self, gamemodel):
        self.gamemodel = gamemodel
        self.lastPly = gamemodel.ply
        if gamemodel.moves and not self.external:
            self.connection.bm.sendMove (
                    toSAN (gamemodel.boards[-2], gamemodel.moves[-1]))
        
        item = self.queue.get(block=True)
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
            print "Error", e.args[0]
            print "moves are", listToSan(gamemodel.boards[0], gamemodel.moves)
            raise PlayerIsDead
        return move
    
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

from collections import defaultdict
from Queue import Queue

from Player import Player, PlayerIsDead, TurnInterrupt
from pychess.Utils.Offer import Offer
from pychess.Utils.Move import parseSAN, toAN, ParsingError, listToSan
from pychess.Utils.const import *
from pychess.Variants import variants

class ICPlayer (Player):
    __type__ = REMOTE
    
    def __init__ (self, gamemodel, name, gameno, color):
        Player.__init__(self)
        
        self.queue = Queue()
        self.okqueue = Queue()
        
        self.name = name
        self.color = color
        self.gameno = gameno
        self.gamemodel = gamemodel
        self.connection = connection = self.gamemodel.connection
        
        self.connections = connections = defaultdict(list)
        connections[connection.bm].append(connection.bm.connect_after("boardUpdate", self.__boardUpdate))
        connections[connection.om].append(connection.om.connect("onOfferAdd", self.__onOfferAdd))
        connections[connection.om].append(connection.om.connect("onOfferRemove", self.__onOfferRemove))
        connections[connection.cm].append(connection.cm.connect("privateMessage", self.__onPrivateMessage))
        
        self.offerToIndex = {}
        self.indexToOffer = {}
        self.lastPly = -1
    
    def getICHandle (self):
        return self.name
    
    #===========================================================================
    #    Handle signals from the connection
    #===========================================================================
    
    def __onOfferAdd (self, om, offer):
        if self.gamemodel.status in UNFINISHED_STATES and self.gamemodel.inControl == True:
            self.indexToOffer[offer.index] = offer
            self.emit ("offer", offer)
    
    def __onOfferRemove (self, om, offer):
        if offer.index in self.indexToOffer:
            self.emit ("withdraw", self.indexToOffer[offer.index])
    
    def __onPrivateMessage (self, cm, name, title, isadmin, text):
        if name == self.name:
            self.emit("offer", Offer(CHAT_ACTION, param=text))
    
    def __boardUpdate (self, bm, gameno, ply, curcol, lastmove, fen, wname, bname, wms, bms):
        if gameno == self.gameno and len(self.gamemodel.players) >= 2 \
            and wname == self.gamemodel.players[0].getICHandle() \
            and bname == self.gamemodel.players[1].getICHandle():
            
            # In some cases (like lost on time) the last move is resent
            if ply <= self.gamemodel.ply:
                return
            self.lastPly = ply
            if 1-curcol == self.color:
                self.queue.put((self.lastPly,lastmove))
                # Ensure the fics thread doesn't continue parsing, before the
                # game/player thread has recieved the move.
                # Specifically this ensures that we aren't killed due to end of
                # game before our last move is recieved
                self.okqueue.get(block=True)
    
    #===========================================================================
    #    Ending the game
    #===========================================================================
    
    def __disconnect (self):
        if self.connections is None: return
        for obj in self.connections:
            for handler_id in self.connections[obj]:
                if obj.handler_is_connected(handler_id):
                    obj.disconnect(handler_id)
        self.connections = None
        
    def end (self, status, reason):
        self.__disconnect()
        self.queue.put("del")
    
    def kill (self, reason):
        self.__disconnect()
        self.queue.put("del")
    
    #===========================================================================
    #    Send the player move updates
    #===========================================================================
    
    def makeMove (self, board1, move, board2):
        self.lastPly = board1.ply
        
        if board2 and self.gamemodel.inControl:
            self.connection.bm.sendMove (toAN (board2, move))
        
        item = self.queue.get(block=True)
        try:
            if item == "del":
                raise PlayerIsDead
            if item == "int":
                raise TurnInterrupt
            
            ply, sanmove = item
            if ply < board1.ply:
                # This should only happen in an observed game
                self.emit("offer", Offer(TAKEBACK_FORCE, param=ply))
            
            try:
                move = parseSAN (board1, sanmove)
            except ParsingError, e:
                raise
            return move
        finally:
            self.okqueue.put("ok")
    
    #===========================================================================
    #    Interacting with the player
    #===========================================================================
    
    def pause (self):
        pass
    
    def resume (self):
        pass
    
    def setBoard (self, fen):
        # setBoard will currently only be called for ServerPlayer when starting
        # to observe some game. In this case FICS already knows how the board
        # should look, and we don't need to set anything
        pass
    
    def undoMoves (self, movecount, gamemodel):
        # If current player has changed so that it is no longer us to move,
        # We raise TurnInterruprt in order to let GameModel continue the game
        if movecount % 2 == 1 and gamemodel.curplayer != self:
            self.queue.put("int")
    
    def putMessage (self, text):
        self.connection.cm.tellPlayer (self.name, text)
    
    #===========================================================================
    #    Offer handling
    #===========================================================================
    
    def offerRematch (self):
        if self.gamemodel.timemodel:
            min = int(self.gamemodel.timemodel.intervals[0][0])/60
            inc = self.gamemodel.timemodel.gain
        else:
            min = 0
            inc = 0
        rated = self.gamemodel.rated
        variant = [ k for (k, v) in variants.iteritems() if variants[k] == self.gamemodel.variant ][0]
        self.connection.om.challenge(self.name, min, inc, rated, variant=variant)
    
    def offer (self, offer):
        self.connection.om.offer(offer, self.lastPly)
    
    def offerDeclined (self, offer):
        pass
    
    def offerWithdrawn (self, offer):
        pass
    
    def offerError (self, offer, error):
        pass

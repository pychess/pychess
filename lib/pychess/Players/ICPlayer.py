from collections import defaultdict
from Queue import Queue

from Player import Player, PlayerIsDead, TurnInterrupt
from pychess.Utils.Move import parseSAN, toAN, ParsingError
from pychess.Utils.Offer import Offer
from pychess.Utils.const import *
from pychess.Variants import variants
from pychess.System.Log import log

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
        connections[connection.om].append(connection.om.connect("onOfferDeclined", self.__onOfferDeclined))
        connections[connection.cm].append(connection.cm.connect("privateMessage", self.__onPrivateMessage))
        
        self.offers = {}
    
    def getICHandle (self):
        return self.name
    
    #===========================================================================
    #    Handle signals from the connection
    #===========================================================================
    
    def __onOfferAdd (self, om, offer):
        if self.gamemodel.status in UNFINISHED_STATES and not self.gamemodel.isObservationGame():
            log.debug("ICPlayer.__onOfferAdd: emitting offer: self.gameno=%s self.name=%s %s\n" % \
                (self.gameno, self.name, offer))
            self.offers[offer.index] = offer
            self.emit ("offer", offer)
    
    def __onOfferDeclined (self, om, offer):
        for offer_ in self.gamemodel.offers.keys():
            if offer.type == offer_.type:
                offer.param = offer_.param
        log.debug("ICPlayer.__onOfferDeclined: emitting decline for %s\n" % offer)
        self.emit("decline", offer)
    
    def __onOfferRemove (self, om, offer):
        if offer.index in self.offers:
            log.debug("ICPlayer.__onOfferRemove: emitting withdraw: self.gameno=%s self.name=%s %s\n" % \
                (self.gameno, self.name, offer))
            self.emit ("withdraw", self.offers[offer.index])
            del self.offers[offer.index]
    
    def __onPrivateMessage (self, cm, name, title, isadmin, text):
        if name == self.name:
            self.emit("offer", Offer(CHAT_ACTION, param=text))
    
    def __boardUpdate (self, bm, gameno, ply, curcol, lastmove, fen, wname, bname, wms, bms):
        log.debug("ICPlayer.__boardUpdate: id(self)=%d self=%s %s %s %s %d %d %s %s %d %d\n" % \
            (id(self), self, gameno, wname, bname, ply, curcol, lastmove, fen, wms, bms))
        
        if gameno == self.gameno and len(self.gamemodel.players) >= 2 \
            and wname == self.gamemodel.players[0].getICHandle() \
            and bname == self.gamemodel.players[1].getICHandle():
            log.debug("ICPlayer.__boardUpdate: id=%d self=%s gameno=%s: this is my move\n" % \
                (id(self), self, gameno))
            
            # In some cases (like lost on time) the last move is resent
            if ply <= self.gamemodel.ply:
                return
            
            if 1-curcol == self.color:
                log.debug("ICPlayer.__boardUpdate: id=%d self=%s ply=%d: putting move=%s in queue\n" % \
                    (id(self), self, ply, lastmove))
                self.queue.put((ply, lastmove))
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
        log.debug("ICPlayer.makemove: id(self)=%d self=%s move=%s board1=%s board2=%s\n" % \
            (id(self), self, move, board1, board2))
        if board2 and not self.gamemodel.isObservationGame():
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
                board1 = self.gamemodel.getBoardAtPly(max(ply-1, 0))
            log.debug("ICPlayer.makemove: id(self)=%d self=%s from queue got: ply=%d sanmove=%s\n" % \
                (id(self), self, ply, sanmove))
            
            try:
                move = parseSAN (board1, sanmove)
                log.debug("ICPlayer.makemove: id(self)=%d self=%s parsed move=%s\n" % \
                    (id(self), self, move))
            except ParsingError, e:
                raise
            return move
        finally:
            log.debug("ICPlayer.makemove: id(self)=%d self=%s returning move=%s\n" % \
                (id(self), self, move))
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
    
    def playerUndoMoves (self, movecount, gamemodel):
        log.debug("ICPlayer.playerUndoMoves: id(self)=%d self=%s, undoing movecount=%d\n" % \
            (id(self), self, movecount))
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
        log.debug("ICPlayer.offer: self=%s %s\n" % (repr(self), offer))
        if offer.type == TAKEBACK_OFFER:
            # only 1 outstanding takeback offer allowed on FICS, so remove any of ours
            indexes = self.offers.keys()
            for index in indexes:
                if self.offers[index].type == TAKEBACK_OFFER:
                    log.debug("ICPlayer.offer: del self.offers[%s] %s\n" % (index, offer))
                    del self.offers[index]
        self.connection.om.offer(offer, self.gamemodel.ply)
    
    def offerDeclined (self, offer):
        log.debug("ICPlayer.offerDeclined: sending decline for %s\n" % offer)
        self.connection.om.decline(offer)
    
    def offerWithdrawn (self, offer):
        pass
    
    def offerError (self, offer, error):
        pass

from pychess.System.Log import log
from pychess.Utils.GameModel import GameModel
from pychess.Utils.Offer import Offer
from pychess.Utils.const import *
from pychess.Players.Human import Human

class ICGameModel (GameModel):
    
    def __init__ (self, connection, gameno, timemodel, variant, rated=False):
        GameModel.__init__(self, timemodel, variant)
        self.connection = connection
        self.gameno = gameno
        
        connections = self.connections
        connections[connection.bm].append(connection.bm.connect("boardUpdate", self.onBoardUpdate))
        connections[connection.bm].append(connection.bm.connect("obsGameEnded", self.onGameEnded))
        connections[connection.bm].append(connection.bm.connect("curGameEnded", self.onGameEnded))
        connections[connection.bm].append(connection.bm.connect("gamePaused", self.onGamePaused))
        connections[connection.om].append(connection.om.connect("onActionError", self.onActionError))
        connections[connection].append(connection.connect("disconnected", self.onDisconnected))
        
        self.inControl = True
        self.rated = rated
    
    def __disconnect (self):
        if self.connections is None: return
        for obj in self.connections:
            # Humans need to stay connected post-game so that "GUI > Actions" works
            if isinstance(obj, Human):
                continue
            
            for handler_id in self.connections[obj]:
                if obj.handler_is_connected(handler_id):
                    obj.disconnect(handler_id)
        self.connections = None
    
    def onBoardUpdate (self, bm, gameno, ply, curcol, lastmove, fen, wname, bname, wms, bms):
        if gameno != self.gameno or len(self.players) < 2 or wname != self.players[0].getICHandle() \
           or bname != self.players[1].getICHandle():
            return
        
        if self.timemodel:
            self.timemodel.updatePlayer (WHITE, wms/1000.)
            self.timemodel.updatePlayer (BLACK, bms/1000.)
        
        if ply < self.ply:
            log.debug("TAKEBACK self.ply: %d, ply: %d" % (self.ply, ply))
            self.undoMoves(self.ply-ply)
    
    def onGameEnded (self, bm, gameno, wname, bname, status, reason):
        if gameno == self.gameno and len(self.players) >= 2 and \
            wname == self.players[0].getICHandle() and bname == self.players[1].getICHandle():
            self.end(status, reason)
    
    def setPlayers (self, players):
        if [player.__type__ for player in players] == [REMOTE, REMOTE]:
            self.inControl = False
        GameModel.setPlayers (self, players)
    
    def onGamePaused (self, bm, gameno, paused):
        if paused:
            self.pause()
        else: self.resume()
        
        # we have to do this here rather than in acceptRecieved(), because
        # sometimes FICS pauses/unpauses a game clock without telling us that the
        # original offer was "accepted"/"received", such as when one player offers
        # "pause" and the other player responds not with "accept" but "pause"
        for offer in self.offers.keys():
            if offer.type in (PAUSE_OFFER, RESUME_OFFER):
                del self.offers[offer]
    
    def onDisconnected (self, connection):
        if self.status in (WAITING_TO_START, PAUSED, RUNNING):
            self.end (KILLED, DISCONNECTED)
    
    ############################################################################
    # Offer management                                                         #
    ############################################################################
    
    def offerRecieved (self, player, offer):
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else: opPlayer = self.players[WHITE]
        
        
        if self.status not in UNFINISHED_STATES and offer.type in INGAME_ACTIONS:
            player.offerError(offer, ACTION_ERROR_REQUIRES_UNFINISHED_GAME)
        
        # TODO: if game is over and opponent is online, send through resume offer
        elif self.status not in UNFINISHED_STATES and offer.type in \
           (TAKEBACK_OFFER, RESUME_OFFER):
            player.offerError(offer, ACTION_ERROR_UNSUPPORTED_FICS_WHEN_GAME_FINISHED)
        
#        elif offer.type == RESUME_OFFER and self.status in (DRAW, WHITEWON,BLACKWON) and \
#           self.reason in UNRESUMEABLE_REASONS:
#            player.offerError(offer, ACTION_ERROR_UNRESUMEABLE_POSITION)
        
        elif offer.type == RESUME_OFFER and self.status != PAUSED:
            player.offerError(offer, ACTION_ERROR_RESUME_REQUIRES_PAUSED)
        
        elif offer.type == CHAT_ACTION:
            opPlayer.putMessage(offer.param)
        
        elif offer.type in (RESIGNATION, FLAG_CALL):
            self.connection.om.offer(offer, self.ply)
        
        elif offer.type == ABORT_OFFER:
            self.connection.om.abort()
        
        elif offer.type == ADJOURN_OFFER:
            self.connection.om.adjourn()
        
        elif offer.type in OFFERS:
            if offer not in self.offers:
                self.offers[offer] = player
                opPlayer.offer(offer)
            # If the offer was an update to an old one, like a new takebackvalue
            # we want to remove the old one from self.offers
            for offer_ in self.offers.keys():
                if offer.type == offer_.type and offer != offer_:
                    del self.offers[offer_]
    
    def acceptRecieved (self, player, offer):
        if player.__type__ == LOCAL:
            if offer not in self.offers or self.offers[offer] == player:
                player.offerError(offer, ACTION_ERROR_NONE_TO_ACCEPT)
            else:
                self.connection.om.accept(offer)
                del self.offers[offer]
        
        # We don't handle any ServerPlayer calls here, as the fics server will
        # know automatically if he/she accepts an offer, and will simply send
        # us the result.
    
    def checkStatus (self):
        if self.status not in (WAITING_TO_START, PAUSED, RUNNING):
            return False
        return True
    
    def onActionError (self, om, offer, error):
        self.emit("action_error", offer, error)
    
    #
    # End
    #
    
    def end (self, status, reason):
        if self.status in UNFINISHED_STATES:
            self.__disconnect()
            
            if self.inControl:
                self.connection.om.offer(Offer(ABORT_OFFER), -1)
                self.connection.om.offer(Offer(RESIGNATION), -1)
            else:
                self.connection.bm.unobserve(self.gameno)
        
        GameModel.end(self, status, reason)

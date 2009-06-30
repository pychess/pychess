
from pychess.System.Log import log
from pychess.Utils.logic import getStatus
from pychess.Utils.GameModel import GameModel
from pychess.Utils.Offer import Offer
from pychess.Utils.const import *

class ICGameModel (GameModel):
    
    def __init__ (self, connection, gameno, timemodel, variant, rated=False):
        GameModel.__init__(self, timemodel, variant)
        self.connection = connection
        self.gameno = gameno
        
        self.connection.bm.connect("boardUpdate", self.onBoardUpdate)
        self.connection.bm.connect("obsGameEnded", self.onGameEnded)
        self.connection.bm.connect("curGameEnded", self.onGameEnded)
        self.connection.bm.connect("gamePaused", self.onGamePaused)
        
        self.connection.om.connect("onActionError", self.onActionError)
        
        self.connection.connect("disconnected", self.onDisconnected)
        
        self.connect("game_terminated", self.afterGameEnded)
        
        self.inControl = True
        self.rated = rated
    
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
        if gameno == self.gameno and len(self.players) >= 2 and wname == self.players[0].getICHandle() \
           and bname == self.players[1].getICHandle():
            self.end (status, reason)
    
    def afterGameEnded (self, self_):
        if not self.inControl:
            self.connection.bm.unobserve(self.gameno)
    
    def setPlayers (self, players):
        if [player.__type__ for player in players] == [REMOTE, REMOTE]:
            self.inControl = False
        GameModel.setPlayers (self, players)
    
    def onGamePaused (self, bm, gameno, paused):
        if paused:
            self.pause()
        else: self.resume()
    
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
        
        # This is only sent by ServerPlayers when observing
        if offer.offerType == TAKEBACK_FORCE:
            self.undoMoves(self.ply - offer.param)
        
        elif offer.offerType == CHAT_ACTION:
            opPlayer.putMessage(offer.param)
        
        elif offer.offerType in (RESIGNATION, FLAG_CALL):
            self.connection.om.offer(offer, self.ply)
        
        elif offer.offerType in OFFERS:
            if offer not in self.offerMap:
                self.offerMap[offer] = player
                opPlayer.offer(offer)
            # If the offer was an update to an old one, like a new takebackvalue
            # we want to remove the old one from offerMap
            for of in self.offerMap.keys():
                if offer.offerType == of.offerType and offer != of:
                    del self.offerMap[of]
    
    def acceptRecieved (self, player, offer):
        if player.__type__ == LOCAL:
            if offer not in self.offerMap or self.offerMap[offer] == player:
                player.offerError(offer, ACTION_ERROR_NONE_TO_ACCEPT)
            else:
                self.connection.om.accept(offer.offerType)
                del self.offerMap[offer]
        
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
    # Terminate
    #
    
    def terminate (self):
        if self.status in UNFINISHED_STATES:
            if self.players[0].__type__ != REMOTE or self.players[1].__type__ != REMOTE:
                self.connection.om.offer(Offer(RESIGNATION), -1)
        GameModel.terminate(self)

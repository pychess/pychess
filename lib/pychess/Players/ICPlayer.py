
from Queue import Queue

from Player import Player, PlayerIsDead, TurnInterrupt
from pychess.Utils.Offer import Offer
from pychess.Utils.Move import parseSAN, toAN, ParsingError, listToSan
from pychess.Utils.const import *

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
        self.connection = self.gamemodel.connection
        
        self.connection.bm.connect("boardUpdate", self.__boardUpdate)
        self.connection.om.connect("onOfferAdd", self.__onOfferAdd)
        self.connection.om.connect("onOfferRemove", self.__onOfferRemove)
        self.connection.cm.connect("privateMessage", self.__onPrivateMessage)
        
        self.offerToIndex = {}
        self.indexToOffer = {}
        self.lastPly = -1
    
    #===========================================================================
    #    Handle signals from the connection
    #===========================================================================
    
    def __onOfferAdd (self, om, index, offer):
        self.indexToOffer[index] = offer
        self.emit ("offer", offer)
    
    def __onOfferRemove (self, om, index):
        if index in self.indexToOffer:
            self.emit ("withdraw", self.indexToOffer[index])
    
    def __onPrivateMessage (self, cm, name, title, isadmin, text):
        if name == self.name:
            self.emit("offer", Offer(CHAT_ACTION, text))
    
    def __boardUpdate (self, bm, gameno, ply, curcol, lastmove, fen, wms, bms):
        if gameno == self.gameno:
            # In some cases (like lost on time) the last move is resent
            if ply <= self.lastPly:
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
    
    def end (self, status, reason):
        self.queue.put("del")
    
    def kill (self, reason):
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
                self.emit("offer", Offer(TAKEBACK_FORCE, ply))
            
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
        self.connection.om.offerRematch()
    
    def offer (self, offer):
        self.connection.om.offer(offer, self.lastPly)
    
    def offerDeclined (self, offer):
        pass
    
    def offerWithdrawn (self, offer):
        pass
    
    def offerError (self, offer, error):
        pass

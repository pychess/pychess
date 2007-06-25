from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

class PlayerIsDead (Exception): pass

class Player (GObject):
    
    __gsignals__ = {
        "offer": (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        "withdraw": (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        "decline": (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        "accept": (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        "dead": (SIGNAL_RUN_FIRST, TYPE_NONE, ())
    }
    
    
    def setName (self, name):
        """ __repr__ should return this name """
        abstract

    def makeMove (self, history):
        """ Takes a history object, concidering the last move as an opponent
            move, and returns a new moveobject with the players answer. """
        abstract
    
    def updateTime (self, secs, opsecs):
        """ Updates the player with the current remaining time as a float of
            seconds """
        pass #Optional
    
    
    def offer (self, offer):
        """ The players opponent has offered the player offer. If the player
            accepts, it should respond by mirroring the offer with
            emit("accept", offer). If it should either ignore the offer or emit
            "decline"."""
        abstract
    
    def offerDeclined (self, offer):
        """ An offer sent by the player was responded negative by the
            opponent """
    
    def offerWithdrawn (self, offer):
        """ An offer earlier offered to the player has been withdrawn """
    
    def offerError (self, offer, error):
        """ An offer, accept or action made by the player has been refused by
            the game model. """
    
    
    def end (self, status, reason):
        """ Called when the game ends in a normal way. Use this for shutting
            down engines etc. """
        pass #Optional
    
    def kill (self, reason):
        """ Called when game has too die fast and ugly. Mostly used in case of
            errors and stuff. Use for closing connections etc. """
        pass #Optional
    
        
    def hurry (self):
        """ Forces engines to move now, and sends a hurry message to nonlocal
            human players """
        pass #Optional
    
    def pause (self):
        """ Should stop the player from thinking until resume is called """
        abstract
        
    def resume (self):
        """ Should resume player to think if he's paused """
        abstract
    
    def setBoard (self, gamemodel):
        pass
    
    def undoMoves (self, move, gamemodel):
        pass
    
    
    def showBoard (self):
        """ Print the board as it the players sees it, e.g. in fen. Used for
            debugging only """
        pass #Optional

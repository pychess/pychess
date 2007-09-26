from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

class PlayerIsDead (Exception):
    """ Used instead of returning a move,
        when an engine crashes, or a nonlocal player disconnects """
    pass

class TurnInterrupt (Exception):
    """ Used instead of returning a move, when a players turn is interupted.
        Currently this will only happen when undoMoves changes the current
        player """
    pass

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
        raise NotImplementedError

    def makeMove (self, history):
        """ Takes a history object, concidering the last move as an opponent
            move, and returns a new moveobject with the players answer. """
        raise NotImplementedError
    
    def updateTime (self, secs, opsecs):
        """ Updates the player with the current remaining time as a float of
            seconds """
        #Optional
    
    
    def offer (self, offer):
        """ The players opponent has offered the player offer. If the player
            accepts, it should respond by mirroring the offer with
            emit("accept", offer). If it should either ignore the offer or emit
            "decline"."""
        raise NotImplementedError
    
    def offerDeclined (self, offer):
        """ An offer sent by the player was responded negative by the
            opponent """
        #Optional
    
    def offerWithdrawn (self, offer):
        """ An offer earlier offered to the player has been withdrawn """
        #Optional
    
    def offerError (self, offer, error):
        """ An offer, accept or action made by the player has been refused by
            the game model. """
        #Optional
    
    def end (self, status, reason):
        """ Called when the game ends in a normal way. Use this for shutting
            down engines etc. """
        raise NotImplementedError
    
    def kill (self, reason):
        """ Called when game has too die fast and ugly. Mostly used in case of
            errors and stuff. Use for closing connections etc. """
        raise NotImplementedError
    
    
    def hurry (self):
        """ Forces engines to move now, and sends a hurry message to nonlocal
            human players """
        #Optional
    
    def pause (self):
        """ Should stop the player from thinking until resume is called """
        raise NotImplementedError
        
    def resume (self):
        """ Should resume player to think if he's paused """
        raise NotImplementedError
    
    def setBoard (self, gamemodel):
        """ Sets the latest board in gamemodel as the current. """
        #Optional
    
    def undoMoves (self, moves, gamemodel):
        """ Undo 'moves' moves and makes the latest board in gamemodel the
            current """
        #Optional
    
    
    def showBoard (self):
        """ Print the board as it the players sees it, e.g. in fen. Used for
            debugging only """
        #Optional

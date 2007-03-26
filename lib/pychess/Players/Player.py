from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

class PlayerIsDead (Exception): pass

class Player (GObject):
    
    __gsignals__ = {
        "action": (SIGNAL_RUN_FIRST, TYPE_NONE, (int,int)),
        "dead": (SIGNAL_RUN_FIRST, TYPE_NONE, ())
    }
    
    def setName (self, name):
        abstract

    def makeMove (self, history):
        """ Takes a history object, concidering the last move as an opponent
            move, and returns a new moveobject with the players answer. """
        abstract

    def offerDraw (self):
        """ Offers the player a draw. Should respond emiting a DRAW_ACCEPTION,
            or simply do nothing"""
        abstract

    def kill (self):
        """ Called in the end of the game, or when the engines is otherwise ment
            to die. Use for closing connections etc. """
        pass #Optional
    
    def showBoard (self):
        """ Print the board as it the players sees it, e.g. in fen. Used for
            debugging only """
        pass #Optional
    
    def hurry (self):
        """ Forces engines to move now, and sends a hurry message to nonlocal
            human players """
        pass #Optional
    
    def updateTime (self, secs, opsecs):
        """ Updates the player with the current remaining time as a float of
            seconds """
        pass #Optional
    
    def pause (self):
        """ Should stop the player from thinking until resume is called """
        raise NotImplementedError #Optional
        
    def resume (self):
        """ Should resume player to think if he's paused """
        raise NotImplementedError #Optional
    
    def undo (self):
        """ Should push back one full move """
        pass

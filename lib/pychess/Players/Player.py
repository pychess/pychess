from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

class Player (GObject):
    
    RESIGNATION, FLAG_CALL, DRAW_OFFER, DRAW_ACCEPTION = range(4)
    __gsignals__ = {
        "action": (SIGNAL_RUN_FIRST, TYPE_NONE, (int,)),
        "dead": (SIGNAL_RUN_FIRST, TYPE_NONE, ())
    }
    
    def setName (self, name):
        abstract

    def makeMove (self, history):
        """ Takes a history object, concidering the last move as an opponent move,
            and returns a new moveobject with the players answer."""
        abstract

    def offerDraw (self):
        """ Offers the player a draw. Should respond emiting a DRAW_ACCEPTION,
            or simply do nothing"""
        abstract

    def __del__ (self):
        """ Called in the end of the game, or when the engines is otherwise ment to die.
            Use for closing connections etc."""
        pass #Optional
    
    def showBoard (self):
        """ Print the board as it the players sees it, e.g. in fen. Used for debugging only """
        pass #Optional
    
    def hurry (self):
        """ Forces engines to move now, and sends a hurry message to nonlocal human players """
        pass #Optional

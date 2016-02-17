from gi.repository import GObject


class PlayerIsDead(Exception):
    """ Used instead of returning a move,
        when an engine crashes, or a nonlocal player disconnects """
    pass


class TurnInterrupt(Exception):
    """ Used instead of returning a move, when a players turn is interrupted.
        Currently this will only happen when undoMoves changes the current
        player """
    pass


class InvalidMove(Exception):
    """ Used instead of returning a move,
        when an engine plays an invalid move """
    pass


class Player(GObject.GObject):

    __gsignals__ = {
        "offer": (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        "withdraw": (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        "decline": (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        "accept": (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        "name_changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.name = ""
        self.ichandle = None
        self.icrating = None

    def setName(self, name):
        """ __repr__ should return this name """
        self.name = name
        self.emit("name_changed")

    def __repr__(self):
        return self.name

    @property
    def time(self):
        pass  # Optional

    # Starting the game

    def prestart(self):
        pass  # Optional

    def start(self):
        pass  # Optional

    def setOptionInitialBoard(self, model):
        pass  # Optional. Further defined in Engine.py

    # Ending the game

    def end(self, status, reason):
        """ Called when the game ends in a normal way. Use this for shutting
            down engines etc. """
        raise NotImplementedError

    def kill(self, reason):
        """ Called when game has too die fast and ugly. Mostly used in case of
            errors and stuff. Use for closing connections etc. """
        raise NotImplementedError

    # Send the player move updates

    def makeMove(self, board1, move, board2):
        """ Takes a board object, and if ply>lowply the latest move object and
            second latest board object as well. Otherwise these two are None.
            Retruns: A new move object, witch the player wants to do. """
        raise NotImplementedError

    def putMove(self, board1, move, board2):
        """ Like makeMove, but doesn't block and doesn't return anything.
            putMove is only used when the player is spectatctor to a game """
        # Optional

    def updateTime(self, secs, opsecs):
        """ Updates the player with the current remaining time as a float of
            seconds """
        # Optional

    # nteracting with the player

    def pause(self):
        """ Should stop the player from thinking until resume is called """
        raise NotImplementedError

    def resume(self):
        """ Should resume player to think if he's paused """
        raise NotImplementedError

    def hurry(self):
        """ Forces engines to move now, and sends a hurry message to nonlocal
            human players """
        # Optional

    def undoMoves(self, moves, gamemodel):
        """ Undo 'moves' moves and makes the latest board in gamemodel the
            current """
        # Optional

    def playerUndoMoves(self, moves, gamemodel):
        """ Some players undo different depending on whether they are players or
            spectators. This is a convenient way to handle that. """
        # Optional
        return self.undoMoves(moves, gamemodel)

    def spectatorUndoMoves(self, moves, gamemodel):
        """ Some players undo different depending on whether they are players or
            spectators. This is a convenient way to handle that. """
        # Optional
        return self.undoMoves(moves, gamemodel)

    def putMessage(self, message):
        """ Sends the player a chatmessage """
        # Optional

    # Offer handling

    def offer(self, offer):
        """ The players opponent has offered the player offer. If the player
            accepts, it should respond by mirroring the offer with
            emit("accept", offer). If it should either ignore the offer or emit
            "decline"."""
        raise NotImplementedError

    def offerDeclined(self, offer):
        """ An offer sent by the player was responded negative by the
            opponent """
        # Optional

    def offerWithdrawn(self, offer):
        """ An offer earlier offered to the player has been withdrawn """
        # Optional

    def offerError(self, offer, error):
        """ An offer, accept or action made by the player has been refused by
            the game model. """
        # Optional

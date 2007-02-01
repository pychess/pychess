
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, GObject
from threading import Lock
from const import *
import datetime
from Board import Board
from pychess.Players.Player import PlayerIsDead
from pychess.System.ThreadPool import pool
from pychess.System.protoopen import protoopen, isWriteable
from logic import getStatus

class GameModel (GObject):
    
    """ GameModel contains all available data on a chessgame.
        It also has the task of controlling players actions and moves """
    
    __gsignals__ = {
        "game_changed":    (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        "game_loaded":     (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        "game_ended":      (SIGNAL_RUN_FIRST, TYPE_NONE, (int,)),
        "draw_sent":       (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        "flag_call_error": (SIGNAL_RUN_FIRST, TYPE_NONE, (object, int))
    }
    
    def __init__ (self, timemodel=None):
        GObject.__init__(self)
        
        self.boards = [Board(setup=True)]
        self.moves = []
        
        self.status = WAITING_TO_START
        
        self.timemodel = timemodel
        if timemodel:
            self.timemodel.connect("timed_out")
        
        today = datetime.date.today()
        self.tags = {
            "Event": _("Local Event"),
            "Site":  _("Local Site"),
            "Round": 1,
            "Year":  today.year,
            "Month": today.month,
            "Day":   today.day
        }
        
        # True if GameModel should not emit game_changed events
        self.freezed = False
        # Set to a Player object who has offered his/her opponent a draw
        self.drawSentBy = None
        # True if the game has been changed since last save
        self.needsSave = False
        # The uri the current game was loaded from, or None if not a loaded game
        self.uri = None
        
        self.applyingMoveLock = Lock()
    
    def setPlayers (self, players):
        assert self.status == WAITING_TO_START
        self.players = players
        for player in self.players:
           player.connect("action", self._actionRecieved)
    
    def setSpectactors (self, spectactors):
        assert self.status == WAITING_TO_START
        self.spectactors = spectactors
    
    ############################################################################
    # Chess stuff                                                              #
    ############################################################################
    
    def applyFen (self, fenstr):
        newBoard = self.boards[-1].fromFen(fenstr)
        self.boards = [newBoard]
        self.moves = []
        if not self.freezed:
            self.emit("game_changed")
    
    def clear (self):
        self.boards = []
        self.moves = []
        self.whiteName = ""
        self.blackName = ""
    
    def _get_ply (self):
        return len(self.moves)
    ply = property(_get_ply)
    
    def _get_curplayer (self):
        return self.players[self.boards[-1].color]
    curplayer = property(_get_curplayer)
    
    ############################################################################
    # Player stuff                                                             #
    ############################################################################
    
    def _actionRecieved (self, player, action):
        
        if action == RESIGNATION:
            if player == self.players[WHITE]:
                self.status = BLACKWON
            else: self.status = WHITEWON
            
            self.emit("game_ended", WON_RESIGN)
        
        elif action == DRAW_OFFER:
            if player == self.players[WHITE]:
                opPlayer = self.players[BLACK]
            else: opPlayer = self.players[WHITE]
            
            if self.drawSentBy == otherPlayer:
                # If our opponent has already offered us a draw, the game ends
                self.status = DRAW
                self.emit("game_ended", DRAW_AGREE)
            else:
                self.emit("draw_sent", player)
                self.drawSentBy = player
                opPlayer.offerDraw()
        
        elif action == FLAG_CALL:
            if not self.timemodel:
                self.emit("flag_call_error", player, NO_TIME_SETTINGS)
                return
            
            if player == self.players[WHITE]:
                opcolor = BLACK
            else: opcolor = WHITE
            
            if self.timemodel.getPlayerTime (opcolor) <= 0:
                if player == self.players[WHITE]:
                    self.status = WHITE_WON
                else: self.status = BLACK_WON
                self.emit("game_ended", WON_CALLFLAG)
                return
            
            self.emit("flag_call_error", player, NOT_OUT_OF_TIME)
    
    ############################################################################
    # Data stuff                                                               #
    ############################################################################
    
    def loadAndStart (self, uri, gameno, position, loader):
        assert self.status == WAITING_TO_START
        
        uriIsFile = type(uri) != str
        if not uriIsFile:
            chessfile = loader.load(protoopen(uri))
        else: chessfile = loader.load(uri)
        
        self.freezeHandlers()
        chessfile.loadToModel(gameno, position, self.model)
        self.thawHandlers()
        self.emit("game_loaded", uri)
        
        self.needSave = False
        if not uriIsFile:
            self.uri = uri
        
        for player in self.players:
            player.setBoard(self)
        for spectactor in self.spectactors:
            spectactor.setBoard(self)
    
    ############################################################################
    # Run stuff                                                                #
    ############################################################################
    
    def start (self):
        pool.start(self._start)
    
    def _start (self):
        self.status = RUNNING
        
        while self.status in (PAUSED, RUNNING):
            curColor = self.boards[-1].color
            curPlayer = self.players[curColor]
            
            if self.timemodel:
                curPlayer.updateTime(self.timemodel.getPlayerTime(curColor))
            
            try:
            	print "Waiting for", curPlayer
                move = curPlayer.makeMove(self)
            except PlayerIsDead:
                # The user of pychess will be informed by an eventhandler in the
                # player object itself, so we just need to break the game loop.
                break
            
            print 1
            self.applyingMoveLock.acquire()
            
            print 2
            newBoard = self.boards[-1].move(move)
            self.boards.append(newBoard)
            self.moves.append(move)
            if not self.freezed:
                self.emit("game_changed")
            
            if self.timemodel:
                self.timemodel.setMovingColor(1-curColor)
            
            print 3
            status = getStatus(self.boards[-1])
            if status != RUNNING:
                self.status, reason = status
                self.emit("game_ended", reason)
                self.applyingMoveLock.release()
                print 4
                break
            
            print 5
            for spectactor in self.spectactors:
                spectactor.makeMove(self)
            
            self.applyingMoveLock.release()
            print 6
    def pause (self):
        """ Players will raise NotImplementedError if they doesn't support
            pause. Spectactors will be ignored. """
        
        for player in self.players:
            player.pause()
        
        try:
            for spectactor in self.spectactors:
                spectactor.pause()
        except NotImplementedError:
            pass
        
        self.applyingMoveLock.acquire()
        if self.timemodel:
            self.timemodel.pause()
        self.applyingMoveLock.release()
        
        self.status = PAUSED
        
    def kill (self):
        if not self.status in (DRAW, WHITEWON, BLACKWON):
            self.status = KILLED
        
        for player in self.players:
            player.kill()
            
        for spectactor in self.spectactors:
            spectactor.kill()
        
        if self.timemodel:
            self.timemodel.pause()
    
    ############################################################################
    # Other stuff                                                              #
    ############################################################################
        
    def undo (self):
        """ Will push back one full move by calling the undo methods of players
            and spectactors. If they raise NotImplementedError we'll try to call
            setBoard instead """
        
        # We really shouldn't do this at the same time we are applying a move
        # On the other hand it shouldn't matter to undo a move while a player is
        # thinking, as the player should be smart enough.
        
        self.applyingMoveLock.acquire()
        
        del self.boards[-2:]
        del self.moves[-2:]
        
        for player in self.players + self.spectactors:
            try:
                player.undo()
            except NotImplementedError:
                player.setBoard(self.boards[-1])
        
        if self.timemodel:
            self.timemodel.undo()
        
        self.applyingMoveLock.release()
    
    def freezeHandlers (self):
        self.freezed = True
    
    def thawHandlers (self):
        self.freezed = False
    
    def isChanged (self):
        if self.needsSave:
            return True
        if not self.uri or not isWriteable (self.uri):
            return True
        return False

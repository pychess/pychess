
from threading import RLock
import traceback
import cStringIO
import datetime

from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, GObject

from pychess.Savers.ChessFile import LoadingError
from pychess.Players.Player import PlayerIsDead, TurnInterrupt
from pychess.System.ThreadPool import pool, PooledThread
from pychess.System.protoopen import protoopen, protosave, isWriteable
from pychess.System.Log import log
from pychess.System import glock
from pychess.Variants.normal import NormalChess

from logic import getStatus, isClaimableDraw
from const import *

class GameModel (GObject, PooledThread):
    
    """ GameModel contains all available data on a chessgame.
        It also has the task of controlling players actions and moves """
    
    __gsignals__ = {
        "game_started":  (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        "game_changed":  (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        "moves_undoing": (SIGNAL_RUN_FIRST, TYPE_NONE, (int,)),
        "game_loading":  (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        "game_loaded":   (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        "game_saved":    (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        "game_ended":    (SIGNAL_RUN_FIRST, TYPE_NONE, (int,)),
        "action_error":  (SIGNAL_RUN_FIRST, TYPE_NONE, (object, int))
    }
    
    def __init__ (self, timemodel=None, variant=NormalChess):
        GObject.__init__(self)

        self.variant = variant
        self.boards = [variant.board(setup=True)]

        self.moves = []
        self.players = []
        
        self.status = WAITING_TO_START
        self.reason = UNKNOWN_REASON
        
        self.timemodel = timemodel
        
        today = datetime.date.today()
        self.tags = {
            "Event": _("Local Event"),
            "Site":  _("Local Site"),
            "Round": 1,
            "Year":  today.year,
            "Month": today.month,
            "Day":   today.day
        }
        
        # Keeps track of offers, so that accepts can be spotted
        self.offerMap = {}
        # True if the game has been changed since last save
        self.needsSave = False
        # The uri the current game was loaded from, or None if not a loaded game
        self.uri = None
        
        self.spectactors = {}
        
        self.applyingMoveLock = RLock()
    
    def setPlayers (self, players):
        assert self.status == WAITING_TO_START
        self.players = players
        for player in self.players:
            player.connect("offer", self.offerRecieved)
            player.connect("withdraw", self.withdrawRecieved)
            player.connect("decline", self.declineRecieved)
            player.connect("accept", self.acceptRecieved)
    
    def setSpectactors (self, spectactors):
        assert self.status == WAITING_TO_START
        self.spectactors = spectactors
    
    ############################################################################
    # Board stuff                                                              #
    ############################################################################
    
    def _get_ply (self):
        return self.boards[-1].ply
    ply = property(_get_ply)
    
    def _get_lowest_ply (self):
        return self.boards[0].ply
    lowply = property(_get_lowest_ply)
    
    def _get_curplayer (self):
        return self.players[self.boards[-1].color]
    curplayer = property(_get_curplayer)
    
    def _plyToIndex (self, ply):
        index = ply - self.boards[0].ply
        if index < 0:
            raise IndexError, "%s < %s" % (ply, self.boards[0].ply)
        return index
    
    def getBoardAtPly (self, ply):
        try:
            return self.boards[self._plyToIndex(ply)]
        except:
            log.debug("%d\t%d\t%d\t%d\n" % (self.lowply, ply, self.ply, len(self.boards)))
            raise
    
    def getMoveAtPly (self, ply):
        return self.moves[self._plyToIndex(ply)]
    
    ############################################################################
    # Offer management                                                         #
    ############################################################################
    
    def offerRecieved (self, player, offer):
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else: opPlayer = self.players[WHITE]
        
        if offer.offerType == HURRY_ACTION:
            opPlayer.hurry()
        
        elif offer.offerType == CHAT_ACTION:
            opPlayer.putMessage(offer.param)
        
        elif offer.offerType == RESIGNATION:
            if player == self.players[WHITE]:
                self.end(BLACKWON, WON_RESIGN)
            else: self.end(WHITEWON, WON_RESIGN)
        
        elif offer.offerType == FLAG_CALL:
            if not self.timemodel:
                player.offerError(offer, ACTION_ERROR_NO_CLOCK)
                return
            
            if player == self.players[WHITE]:
                opcolor = BLACK
            else: opcolor = WHITE
            
            if self.timemodel.getPlayerTime (opcolor) <= 0:
                if self.timemodel.getPlayerTime (1-opcolor) <= 0:
                    self.end(DRAW, DRAW_CALLFLAG)
                else:
                    if player == self.players[WHITE]:
                        self.end(WHITEWON, WON_CALLFLAG)
                    else:
                        self.end(BLACKWON, WON_CALLFLAG)
            else:
                player.offerError(offer, ACTION_ERROR_NOT_OUT_OF_TIME)
        
        elif offer.offerType == DRAW_OFFER and isClaimableDraw(self.boards[-1]):
            reason = getStatus(self.boards[-1])[1]
            self.end(DRAW, reason)
        
        elif offer.offerType in OFFERS:
            if offer.offerType == TAKEBACK_OFFER and offer.param < self.lowply:
                player.offerError(offer, ACTION_ERROR_TO_LARGE_UNDO)
                return
            if offer not in self.offerMap:
                self.offerMap[offer] = player
                opPlayer.offer(offer)
            # If we updated an older offer, we want to delete the old one
            for of in self.offerMap.keys():
                if offer.offerType == of.offerType and offer != of:
                    del self.offerMap[of]
    
    def withdrawRecieved (self, player, offer):
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else: opPlayer = self.players[WHITE]
        
        if offer in self.offerMap and self.offerMap[offer] == player:
            del self.offerMap[offer]
            opPlayer.offerWithdrawn(offer)
        else:
            player.offerError(offer, ACTION_ERROR_NONE_TO_WITHDRAW)
    
    def declineRecieved (self, player, offer):
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else: opPlayer = self.players[WHITE]
        
        if offer in self.offerMap and self.offerMap[offer] == opPlayer:
            del self.offerMap[offer]
            opPlayer.offerDeclined(offer)
        else:
            player.offerError(offer, ACTION_ERROR_NONE_TO_DECLINE)
    
    def acceptRecieved (self, player, offer):
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else: opPlayer = self.players[WHITE]
        
        if offer in self.offerMap and self.offerMap[offer] == opPlayer:
            if offer.offerType == DRAW_OFFER:
                self.end(DRAW, DRAW_AGREE)
            elif offer.offerType == TAKEBACK_OFFER:
                self.undoMoves(self.ply - offer.param)
            elif offer.offerType == ADJOURN_OFFER:
                self.end(ADJOURNED, ADJOURNED_AGREEMENT)
            elif offer.offerType == ABORT_OFFER:
                self.end(ABORTED, ABORTED_AGREEMENT)
            elif offer.offerType == PAUSE_OFFER:
                self.pause()
            elif offer.offerType == RESUME_OFFER:
                self.resume()
            del self.offerMap[offer]
        else:
            player.offerError(offer, ACTION_ERROR_NONE_TO_ACCEPT)
    
    ############################################################################
    # Data stuff                                                               #
    ############################################################################
    
    def loadAndStart (self, uri, loader, gameno, position):
        assert self.status == WAITING_TO_START
        
        uriIsFile = type(uri) != str
        if not uriIsFile:
            chessfile = loader.load(protoopen(uri))
        else: 
            chessfile = loader.load(uri)
        
        self.emit("game_loading")
        try:
            chessfile.loadToModel(gameno, position, self)
        #Postpone error raising to make games loadable to the point of the error
        except LoadingError, e:
            error = e
        else: error = None
        self.emit("game_loaded", uri)
        
        self.needsSave = False
        if not uriIsFile:
            self.uri = uri
        else: self.uri = None
        
        if self.status == RUNNING:
            for player in self.players:
                player.setBoard(self)
            for spectactor in self.spectactors.values():
                spectactor.setBoard(self)
            
            if self.timemodel:
                self.timemodel.setMovingColor(self.boards[-1].color)
                if self.ply >= 2:
                    self.timemodel.start()
            
            self.status = WAITING_TO_START
            self.start()
        else:
            self.emit("game_started")
        
        if self.status == WHITEWON:
            self.emit("game_ended", self.reason)
        
        elif self.status == BLACKWON:
            self.emit("game_ended", self.reason)
        
        elif self.status == DRAW:
            self.emit("game_ended", self.reason)
        
        if error:
            raise error
    
    def save (self, uri, saver, append):
        if type(uri) == str:
            fileobj = protosave(uri, append)
            self.uri = uri
        else:
            fileobj = uri
            self.uri = None
        saver.save(fileobj, self)
        self.emit("game_saved", uri)
        self.needsSave = False
        
    ############################################################################
    # Run stuff                                                                #
    ############################################################################
    
    def run (self):
        # Avoid racecondition when self.start is called while we are in self.end
        if self.status != WAITING_TO_START:
            return
        
        self.status = RUNNING
        self.emit("game_started")
        
        while self.status in (PAUSED, RUNNING):
            curColor = self.boards[-1].color
            curPlayer = self.players[curColor]
            
            if self.timemodel:
                curPlayer.updateTime(self.timemodel.getPlayerTime(curColor),
                                     self.timemodel.getPlayerTime(1-curColor))
            
            try:
                move = curPlayer.makeMove(self)
            except PlayerIsDead, e:
                if self.status in (WAITING_TO_START, PAUSED, RUNNING):
                    stringio = cStringIO.StringIO()
                    traceback.print_exc(file=stringio)
                    error = stringio.getvalue()
                    log.error("A Player died:%s\n%s" % (e, error), curPlayer)
                    if curColor == WHITE:
                        self.kill(WHITE_ENGINE_DIED)
                    else: self.kill(BLACK_ENGINE_DIED)
                break
            except TurnInterrupt:
                continue
            
            self.applyingMoveLock.acquire()
            try:
                self.needsSave = True
                newBoard = self.boards[-1].move(move)
                self.boards.append(newBoard)
                self.moves.append(move)
                if self.timemodel:
                    self.timemodel.tap()
                if not self.checkStatus():
                    break
                self.emit("game_changed")
                
                for spectactor in self.spectactors.values():
                    model = GameModel()
                    model.boards = [board.clone() for board in self.boards]
                    model.moves = [move for move in self.moves]
                    model.players = self.players
                    model.status = self.status
                    model.reason = self.reason
                    spectactor.makeMove(model)
            finally:
                self.applyingMoveLock.release()
    
    def checkStatus (self):
        if self.status not in (WAITING_TO_START, PAUSED, RUNNING):
            return False
        status, reason = getStatus(self.boards[-1])
        if status not in (WAITING_TO_START, PAUSED, RUNNING):
            self.status = status
            self.emit("game_changed")
            self.status = RUNNING # self.end only accepts ending if running
            self.end(status, reason)
            return False
        
        return True
    
    def pause (self):
        """ Players will raise NotImplementedError if they doesn't support
            pause. Spectactors will be ignored. """
        
        glock.release()
        self.applyingMoveLock.acquire()
        glock.acquire()
        try:
            for player in self.players:
                player.pause()
            
            try:
                for spectactor in self.spectactors.values():
                    spectactor.pause()
            except NotImplementedError:
                pass
            
            if self.timemodel:
                self.timemodel.pause()
            
            self.status = PAUSED
        finally:
            glock.release()
            self.applyingMoveLock.release()
            glock.acquire()
    
    def resume (self):
        
        glock.release()
        self.applyingMoveLock.acquire()
        glock.acquire()
        try:
            for player in self.players:
                player.resume()
            
            try:
                for spectactor in self.spectactors.values():
                    spectactor.resume()
            except NotImplementedError:
                pass
            
            if self.timemodel:
                self.timemodel.resume()
            
            self.status = RUNNING
        finally:
            glock.release()
            self.applyingMoveLock.release()
    
    def end (self, status, reason):
        if not self.status in (WAITING_TO_START, PAUSED, RUNNING):
            return
        
        log.debug("Ending a game with status %d for reason %d\n%s" % (status, reason,
            "".join(traceback.format_list(traceback.extract_stack())).strip()))
        self.status = status
        
        for player in self.players:
            player.end(self.status, self.reason)
        
        for spectactor in self.spectactors.values():
            spectactor.end(self.status, self.reason)
        
        if self.timemodel:
            self.timemodel.pause()
        
        self.needsSave = True
        self.emit("game_ended", reason)
    
    def kill (self, reason):
        if not self.status in (WAITING_TO_START, PAUSED, RUNNING):
            return
        
        log.debug("Killing a game for reason %d\n%s" % (reason,
            "".join(traceback.format_list(traceback.extract_stack())).strip()))
        self.status = KILLED
        self.reason = reason
        
        for player in self.players:
            player.kill(reason)
        
        for spectactor in self.spectactors.values():
            spectactor.kill(reason)
        
        if self.timemodel:
            self.timemodel.pause()
        
        self.emit("game_ended", reason)
    
    ############################################################################
    # Other stuff                                                              #
    ############################################################################
    
    def undoMoves (self, moves):
        """ Will push back one full move by calling the undo methods of players
            and spectactors. If they raise NotImplementedError we'll try to call
            setBoard instead """
        
        # We really shouldn't do this at the same time we are applying a move
        # On the other hand it shouldn't matter to undo a move while a player is
        # thinking, as the player should be smart enough.
        
        self.emit("moves_undoing", moves)
        
        self.applyingMoveLock.acquire()
        try:
            self.needsSave = True
            
            del self.boards[-moves:]
            del self.moves[-moves:]
            
            for player in list(self.players) + list(self.spectactors.values()):
                try:
                    player.undoMoves(moves, self)
                except NotImplementedError:
                    # If the player doesn't support undoing, we might be able to
                    # simply "load" the new last board
                    player.setBoard(self)
            
            if self.timemodel:
                self.timemodel.undoMoves(moves)
        finally:
            self.applyingMoveLock.release()
    
    def isChanged (self):
        if self.ply == 0:
            return False
        if self.needsSave:
            return True
        if not self.uri or not isWriteable (self.uri):
            return True
        return False

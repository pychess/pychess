from Queue import Queue

import gtk, gobject

from pychess.Utils.const import *
from pychess.Utils.Offer import Offer
from pychess.System.Log import log
from pychess.System import glock, conf
from pychess.widgets.gamewidget import cur_gmwidg

from Player import Player, PlayerIsDead, TurnInterrupt

OFFER_MESSAGES = {
    DRAW_OFFER:
        (_("Your opponent has offered you a draw. Accept?"),
         _("Your opponent has offered you a draw. If you accept this offer, the game will end with a score of 1/2 - 1/2."), False),
    ABORT_OFFER:
        (_("Your opponent wants to abort the game. Accept?"),
         _("Your opponent has asked that the game be aborted. If you accept this offer, the game will end with no rating change."), False),
    ADJOURN_OFFER:
        (_("Your opponent wants to adjourn the game. Accept?"),
         _("Your opponent has asked that the game be adjourned. If you accept this offer, the game will be adjourned and you can resume it later (when your opponent is online and both players agree to resume)."), False),
    TAKEBACK_OFFER:
        (_("Your opponent wants to undo %s move(s). Accept?"),
         _("Your opponent has asked that the last %s move(s) be undone. If you accept this offer, the game will continue from the earlier position."), True),
    PAUSE_OFFER:
        (_("Your opponent wants to pause the game. Accept?"),
         _("Your opponent has asked that the game be paused. If you accept this offer, the game clock will be paused until both players agree to resume the game."), False),
    RESUME_OFFER:
        (_("Your opponent wants to resume the game. Accept?"),
         _("Your opponent has asked that the game be resumed. If you accept this offer, the game clock will continue from where it was paused."), False)
}

ACTION_NAMES = {
    RESIGNATION: _("The resignation"),
    FLAG_CALL: _("The flag call"),
    DRAW_OFFER: _("The draw offer"),
    ABORT_OFFER: _("The abort offer"),
    ADJOURN_OFFER: _("The adjourn offer"),
    PAUSE_OFFER: _("The pause offer"),
    RESUME_OFFER: _("The resume offer"),
    SWITCH_OFFER: _("The offer to switch sides"),
    TAKEBACK_OFFER: _("The takeback offer"),
}

ACTION_ACTIONS = {
    RESIGNATION: _("resign"),
    FLAG_CALL: _("call your opponents flag"),
    DRAW_OFFER: _("offer a draw"),
    ABORT_OFFER: _("offer an abort"),
    ADJOURN_OFFER: _("offer to adjourn"),
    PAUSE_OFFER: _("offer a pause"),
    RESUME_OFFER: _("offer to resume"),
    SWITCH_OFFER: _("offer to switch sides"),
    TAKEBACK_OFFER: _("offer a takeback"),
    HURRY_ACTION: _("ask your opponent to move")
}

ERROR_MESSAGES = {
    ACTION_ERROR_NO_CLOCK:
        _("The game hasn't got a clock."),
    ACTION_ERROR_NOT_OUT_OF_TIME:
        _("Your opponent is not out of time."),
    ACTION_ERROR_CLOCK_NOT_STARTED:
        _("The clock hasn't been started yet."),
    ACTION_ERROR_SWITCH_UNDERWAY:
        _("You can't switch colors during the game."),
    ACTION_ERROR_TOO_LARGE_UNDO:
        _("You have tried to undo too many moves."),
    ACTION_ERROR_GAME_ENDED:
        _("You can not offer a takeback because your opponent is not available."),
    ACTION_ERROR_REQUIRES_UNFINISHED_GAME:
        _("You can not %s when the game is over."),
    ACTION_ERROR_UNRESUMEABLE_POSITION:
        _("The game can not be resumed because the current position is not legally playable."),
    ACTION_ERROR_RESUME_REQUIRES_PAUSED:
        _("You can not resume a game that is not paused."),
    ACTION_ERROR_UNSUPPORTED_FICS_WHEN_GAME_FINISHED:
        _("You can not %s on FICS when the game is over."),
}

class Human (Player):
    __type__ = LOCAL
    
    __gsignals__ = {
        "messageRecieved": (gobject.SIGNAL_RUN_FIRST, None, (str,)),
    }
    
    def __init__ (self, gmwidg, color, name, ichandle=None):
        Player.__init__(self)
        
        self.defname = "Human"
        self.board = gmwidg.board
        self.gmwidg = gmwidg
        self.gamemodel = self.board.view.model
        self.queue = Queue()
        self.color = color
        self.conid = [
            self.board.connect("piece_moved", self.piece_moved),
            self.board.connect("action", lambda b,action,param: self.emit_action(action, param))
        ]
        self.setName(name)
        self.ichandle = ichandle
        
        if self.gamemodel.timemodel:
            self.gamemodel.timemodel.connect('zero_reached', self.zero_reached)
    
    def getICHandle (self):
        return self.ichandle
    
    #===========================================================================
    #    Handle signals from the board
    #===========================================================================
    
    def zero_reached (self, timemodel, color):
        if conf.get('autoCallFlag', False) and \
                self.gamemodel.status == RUNNING and \
                timemodel.getPlayerTime(1-self.color) <= 0:
            log.log('Automatically sending flag call on behalf of player %s.' % self.name)
            self.emit("offer", Offer(FLAG_CALL)) 
    
    def piece_moved (self, board, move, color):
        if color != self.color:
            return
        self.queue.put(move)
    
    def emit_action (self, action, param):
        # If there are two or more tabs open, we have to ensure us that it is
        # us who are in the active tab, and not the others
        if self.gmwidg != cur_gmwidg():
            return
        # If there are two human players, we have to ensure us that it was us
        # who did the action, and not the others
        if self.gamemodel.players[1-self.color].__type__ == LOCAL:
            if action == HURRY_ACTION:
                if self.gamemodel.boards[-1].color == self.color:
                    return
            else:
                if self.gamemodel.boards[-1].color != self.color:
                    return
        self.emit("offer", Offer(action, param=param))
    
    #===========================================================================
    #    Send the player move updates
    #===========================================================================
    
    def makeMove (self, board1, move, board2):
        self.gmwidg.setLocked(False)
        item = self.queue.get(block=True)
        self.gmwidg.setLocked(True)
        if item == "del":
            raise PlayerIsDead, "Killed by foreign forces"
        if item == "int":
            raise TurnInterrupt
        return item
    
    #===========================================================================
    #    Ending the game
    #===========================================================================
    
    def end (self, status, reason):
        self.queue.put("del")
    
    def kill (self, reason):
        print "I am killed", self
        for id in self.conid:
            if self.board.handler_is_connected(id):
                self.board.disconnect(id)
        self.queue.put("del")
    
    #===========================================================================
    #    Interacting with the player
    #===========================================================================
    
    def hurry (self):
        title = _("Your opponent asks you to hurry!")
        description = _("Generally this means nothing, as the game is timebased, but if you want to please your opponent, perhaps you should get going.")
        self._message(title, description, gtk.MESSAGE_INFO, gtk.BUTTONS_OK)
        
    @glock.glocked
    def pause (self):
        self.gmwidg.setLocked(True)
    
    @glock.glocked
    def resume (self):
        if self.board.view.model.curplayer == self:
            self.gmwidg.setLocked(False)
    
    def playerUndoMoves (self, movecount, gamemodel):
        #If the movecount is odd, the player has changed, and we have to interupt
        if movecount % 2 == 1:
            # If it is no longer us to move, we raise TurnInterruprt in order to
            # let GameModel continue the game.
            if gamemodel.curplayer != self:
                log.debug("Human.playerUndoMoves(): putting TurnInterrupt into self.queue\n")
                self.queue.put("int")
        
        # If the movecount is even, we have to ensure the board is unlocked.
        # This is because it might have been locked by the game ending, but
        # perhaps we have now undone some moves, and it is no longer ended.
        elif movecount % 2 == 0 and gamemodel.curplayer == self:
            self.gmwidg.setLocked(False)
    
    def putMessage (self, text):
        self.emit("messageRecieved", text)
    
    def sendMessage (self, text):
        self.emit("offer", Offer(CHAT_ACTION, param=text))
    
    #===========================================================================
    #    Offer handling
    #===========================================================================
    
    def offer (self, offer):
        title, description, takesParam = OFFER_MESSAGES[offer.type]
        if takesParam:
            param = offer.param
            if offer.type == TAKEBACK_OFFER and \
                    self.gamemodel.players[1-self.color].__type__ is not REMOTE:
                param = self.gamemodel.ply - offer.param
            title = title % param
            description = description % param
        
        def responsecb (dialog, response):
            if response == gtk.RESPONSE_YES:
                self.emit("accept", offer)
            else: self.emit("decline", offer)
        self._message(title, description,
                gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, responsecb)
    
    def offerDeclined (self, offer):
        if offer.type not in ACTION_NAMES:
            return
        title = _("%s was declined by your opponent") % ACTION_NAMES[offer.type]
        description = _("You can try to send the offer to your opponent later in the game again.")
        self._message(title, description, gtk.MESSAGE_INFO, gtk.BUTTONS_OK)
    
    def offerWithdrawn (self, offer):
        if offer.type not in ACTION_NAMES:
            return
        title = _("%s was withdrawn by your opponent") % ACTION_NAMES[offer.type]
        description = _("Your opponent seems to have changed his or her mind.")
        self._message(title, description, gtk.MESSAGE_INFO, gtk.BUTTONS_OK)
    
    def offerError (self, offer, error):
        if offer.type not in ACTION_NAMES:
            return
        actionName = ACTION_NAMES[offer.type]
        if error == ACTION_ERROR_NONE_TO_ACCEPT:
            title = _("Unable to accept %s") % actionName.lower()
            description = _("PyChess was unable to get the %s offer accepted. Probably because it has been withdrawn.")
        elif error == ACTION_ERROR_REQUIRES_UNFINISHED_GAME or \
           error == ACTION_ERROR_UNSUPPORTED_FICS_WHEN_GAME_FINISHED:
            if offer.type not in ACTION_ACTIONS: return
            title = _("Game is not running")
            description = ERROR_MESSAGES[error] % ACTION_ACTIONS[offer.type]
        elif error == ACTION_ERROR_NONE_TO_DECLINE or \
             error == ACTION_ERROR_NONE_TO_WITHDRAW:
            # If the offer was not there, it has probably already been either
            # declined or withdrawn.
            return
        else:
            title = _("%s returns an error") % actionName
            description = ERROR_MESSAGES[error]
        self._message(title, description, gtk.MESSAGE_INFO, gtk.BUTTONS_OK)
    
    @glock.glocked
    def _message (self, title, description, type, buttons, responsecb=(lambda d,r:None)):
        d = gtk.MessageDialog (type=type, buttons=buttons)
        d.set_markup ("<big><b>%s</b></big>" % title)
        d.format_secondary_text (description)
        def response (dialog, response, responsecb):
            responsecb(dialog, response)
            dialog.hide()
        d.connect("response", response, responsecb)
        d.show()

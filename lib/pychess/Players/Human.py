from Queue import Queue

import gtk, gobject

from pychess.Utils.const import *
from pychess.Utils.Offer import Offer
from pychess.System import glock
from pychess.widgets.gamewidget import cur_gmwidg

from Player import Player, PlayerIsDead, TurnInterrupt

OFFER_MESSAGES = {
    DRAW_OFFER:
        (_("You've got a draw offer. Accept?"),
         _("Your opponent has offered you a draw. If you accept it the game will end with score 1/2 - 1/2."), False),
    ABORT_OFFER:
        (_("You've got an abort offer. Accept?"),
         _("Your opponent has offered you to abort the game. If you accept, the game will end with no rating change."), False),
    ADJOURN_OFFER:
        (_("You've got an adjourn offer. Accept?"),
         _("Your opponent has offered you to adjourn the game. If you accept, the game will adjourned, and you can later resume it (If your opponent is online and willing)."), False),
    TAKEBACK_OFFER:
        (_("Your opponent wants to undo. Accept?"),
         _("Your opponent wants to undo back to halfmove %s.. If you accept, the game will continue from the earlier position."), True),
    PAUSE_OFFER:
        (_("Your opponent offers you a pause. Accept?"),
         _("Your opponent wants to make a break. If you accept the game clock will be paused until on of you accept a resume offer"), False),
    RESUME_OFFER:
        (_("Your opponent wants to resume. Accept?"),
         _("Your opponent wants to resume the game. If you accept, the game clock will start counting down from where it was left."), False)
}

ACTION_NAMES = {
    RESIGNATION: _("the resignation"),
    FLAG_CALL: _("the flag call"),
    DRAW_OFFER: _("the draw offer"),
    ABORT_OFFER: _("the abort offer"),
    ADJOURN_OFFER: _("the adjourn offer"),
    PAUSE_OFFER: _("the pause offer"),
    RESUME_OFFER: _("the resume offer"),
    SWITCH_OFFER: _("the offer to switch sides"),
    TAKEBACK_OFFER: _("the takeback offer")
}

ERROR_MESSAGES = {
    ACTION_ERROR_NO_CLOCK:
        _("The game hasn't got a clock."),
    ACTION_ERROR_NOT_OUT_OF_TIME:
        _("Your opponent is not out of time."),
    ACTION_ERROR_CLOCK_NOT_STARTED:
        _("The clock hasn't yet been started."),
    ACTION_ERROR_SWITCH_UNDERWAY:
        _("You can't switch color during the game."),
    ACTION_ERROR_TOO_LARGE_UNDO:
        _("You have tried to redo to many moves."),
    ACTION_ERROR_GAME_ENDED:
        _("You can't undo a game, which has ended in an unnatural way."),
}

class Human (Player):
    __type__ = LOCAL
    
    __gsignals__ = {
        "messageRecieved": (gobject.SIGNAL_RUN_FIRST, None, (str,)),
    }
    
    def __init__ (self, gmwidg, color, name):
        Player.__init__(self)
        
        self.defname = "Human"
        self.board = gmwidg.board
        self.gmwidg = gmwidg
        self.gamemodel = self.board.view.model
        self.queue = Queue()
        self.color = color
        self.conid = [
            self.board.connect("piece_moved", self.piece_moved),
            self.board.connect("action", lambda b,ac,pa: self.emit_action(ac,pa))
        ]
        self.setName(name)
    
    #===========================================================================
    #    Handle signals from the board
    #===========================================================================
    
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
        self.emit("offer", Offer(action, param))
    
    #===========================================================================
    #    Send the player move updates
    #===========================================================================
    
    def makeMove (self, board1, move, board2):
        self.gmwidg.setLocked(False)
        item = self.queue.get(block=True)
        self.gmwidg.setLocked(True)
        if item == "del":
            raise PlayerIsDead, "Killed by forgin forces"
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
    
    def undoMoves (self, movecount, gamemodel):
        #If the movecount is odd, the player has changed, and we have to interupt
        if movecount % 2 == 1:
            # If it is no longer us to move, we raise TurnInterruprt in order to
            # let GameModel continue the game.
            if gamemodel.curplayer != self:
                self.queue.put("int")
        
        # If the movecount is even, we have to ensure the board is unlocked.
        # This is because it might have been locked by the game ending, but
        # perhaps we have now undone some moves, and it is no longer ended.
        elif movecount % 2 == 0 and gamemodel.curplayer == self:
            self.gmwidg.setLocked(False)
    
    def putMessage (self, text):
        self.emit("messageRecieved", text)
    
    def sendMessage (self, text):
        self.emit("offer", Offer(CHAT_ACTION, text))
    
    #===========================================================================
    #    Offer handling
    #===========================================================================
    
    def offer (self, offer):
        title, description, takesParam = OFFER_MESSAGES[offer.offerType]
        if takesParam:
            description = description % offer.param
        
        def response (dialog, response):
            if response == gtk.RESPONSE_YES:
                self.emit("accept", offer)
            else: self.emit("decline", offer)
        self._message(title, description,
                gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, response)
    
    def offerDeclined (self, offer):
        if offer.offerType not in ACTION_NAMES:
            return
        title = _("%s was declined by your opponent") % ACTION_NAMES[offer.offerType]
        description = _("You can try to send the offer to your opponent later in the game again.")
        self._message(title, description, gtk.MESSAGE_INFO, gtk.BUTTONS_OK)
    
    def offerWithdrawn (self, offer):
        if offer.offerType not in ACTION_NAMES:
            return
        title = _("%s was withdrawn by your opponent") % ACTION_NAMES[offer.offerType]
        description = _("Your opponent seams to have changed his or her mind.")
        self._message(title, description, gtk.MESSAGE_INFO, gtk.BUTTONS_OK)
    
    def offerError (self, offer, error):
        if offer.offerType not in ACTION_NAMES:
            return
        actionName = ACTION_NAMES[offer.offerType]
        if error == ACTION_ERROR_NONE_TO_ACCEPT:
            title = _("Unable to accept %s") % actionName
            description = _("PyChess was unable to get the %s offer accepted. Probably because it has been withdrawn.")
        elif error == ACTION_ERROR_NONE_TO_DECLINE or \
             error == ACTION_ERROR_NONE_TO_WITHDRAW:
            # If the offer was not there, it has probably already been either
            # declined or withdrawn.
            return
        else:
            title = _("%s returns an error") % (actionName[0].upper()+actionName[1:])
            description = ERROR_MESSAGES[error]
        self._message(title, description, gtk.MESSAGE_INFO, gtk.BUTTONS_OK)
    
    @glock.glocked
    def _message (self, title, description, type, buttons, resfunc=(lambda d,r:None)):
        d = gtk.MessageDialog (type=type, buttons=buttons)
        d.set_markup ("<big><b>%s</b></big>" % title)
        d.format_secondary_text (description)
        def response (dialog, response):
            resfunc(dialog, response)
            d.hide()
        d.connect("response", response)
        d.show()



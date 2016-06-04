from __future__ import print_function

from gi.repository import Gtk, GObject

from pychess.compat import Queue
from pychess.Utils.const import DRAW_OFFER, ABORT_OFFER, ADJOURN_OFFER, TAKEBACK_OFFER, \
    PAUSE_OFFER, RESUME_OFFER, RESIGNATION, FLAG_CALL, SWITCH_OFFER, HURRY_ACTION, \
    ACTION_ERROR_NOT_OUT_OF_TIME, ACTION_ERROR_CLOCK_NOT_STARTED, ACTION_ERROR_SWITCH_UNDERWAY, \
    ACTION_ERROR_TOO_LARGE_UNDO, ACTION_ERROR_NONE_TO_WITHDRAW, ACTION_ERROR_NONE_TO_ACCEPT, \
    LOCAL, RUNNING, CHAT_ACTION, REMOTE, ACTION_ERROR_NONE_TO_DECLINE
from pychess.Utils.logic import validate
from pychess.Utils.Move import Move
from pychess.Utils.Offer import Offer
from pychess.System.idle_add import idle_add
from pychess.System.Log import log
from pychess.System import conf

from pychess.Players.Player import Player, PlayerIsDead, TurnInterrupt
from pychess.widgets.InfoBar import InfoBarMessage, InfoBarMessageButton
from pychess.widgets import InfoBar

OFFER_MESSAGES = {
    DRAW_OFFER:
    (_("Your opponent has offered you a draw."),
     _("Your opponent has offered you a draw. If you accept this offer, the game will end with a score of 1/2 - 1/2."), False),
    ABORT_OFFER:
    (_("Your opponent wants to abort the game."),
     _("Your opponent has asked that the game be aborted. If you accept this offer, the game will end with no rating change."), False),
    ADJOURN_OFFER:
    (_("Your opponent wants to adjourn the game."),
     _("Your opponent has asked that the game be adjourned. If you accept this offer, the game will be adjourned and you can resume it later (when your opponent is online and both players agree to resume)."), False),
    TAKEBACK_OFFER:
    (_("Your opponent wants to undo %s move(s)."),
     _("Your opponent has asked that the last %s move(s) be undone. If you accept this offer, the game will continue from the earlier position."), True),
    PAUSE_OFFER:
    (_("Your opponent wants to pause the game."),
     _("Your opponent has asked that the game be paused. If you accept this offer, the game clock will be paused until both players agree to resume the game."), False),
    RESUME_OFFER:
    (_("Your opponent wants to resume the game."),
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
    ACTION_ERROR_NOT_OUT_OF_TIME: _("Your opponent is not out of time."),
    ACTION_ERROR_CLOCK_NOT_STARTED: _("The clock hasn't been started yet."),
    ACTION_ERROR_SWITCH_UNDERWAY:
    _("You can't switch colors during the game."),
    ACTION_ERROR_TOO_LARGE_UNDO: _("You have tried to undo too many moves."),
}


class Human(Player):
    __type__ = LOCAL

    __gsignals__ = {
        "messageReceived": (GObject.SignalFlags.RUN_FIRST, None, (str, )),
    }

    def __init__(self, gmwidg, color, name, ichandle=None, icrating=None):
        Player.__init__(self)

        self.defname = "Human"
        self.board = gmwidg.board
        self.gmwidg = gmwidg
        self.gamemodel = self.gmwidg.gamemodel
        self.queue = Queue()
        self.color = color

        self.board_cids = [
            self.board.connect("piece_moved", self.piece_moved),
            self.board.connect("action", self.emit_action)
        ]
        self.setName(name)
        self.ichandle = ichandle
        self.icrating = icrating

        if self.gamemodel.timed:
            self.timemodel_cid = self.gamemodel.timemodel.connect('zero_reached', self.zero_reached)
        self.cid = self.gamemodel.connect_after("game_terminated", self.on_game_terminated)

    def on_game_terminated(self, model):
        for cid in self.board_cids:
            self.board.disconnect(cid)
        if self.gamemodel.timed:
            self.gamemodel.timemodel.disconnect(self.timemodel_cid)
        self.gamemodel.disconnect(self.cid)

    # Handle signals from the board

    def zero_reached(self, timemodel, color):
        if conf.get('autoCallFlag', False) and \
                self.gamemodel.status == RUNNING and \
                timemodel.getPlayerTime(1 - self.color) <= 0:
            log.info('Automatically sending flag call on behalf of player %s.'
                     % self.name)
            self.emit("offer", Offer(FLAG_CALL))

    def piece_moved(self, board, move, color):
        if color != self.color:
            return
        self.queue.put(move)

    def emit_action(self, board, action, param):
        # If there are two or more tabs open, we have to ensure us that it is
        # us who are in the active tab, and not the others
        if not self.gmwidg.isInFront():
            return
        log.debug("Human.emit_action: self.name=%s, action=%s" %
                  (self.name, action))

        # If there are two human players, we have to ensure us that it was us
        # who did the action, and not the others
        if self.gamemodel.players[1 - self.color].__type__ == LOCAL:
            if action == HURRY_ACTION:
                if self.gamemodel.boards[-1].color == self.color:
                    return
            else:
                if self.gamemodel.boards[-1].color != self.color:
                    return
        self.emit("offer", Offer(action, param=param))

    # Send the player move updates

    def makeMove(self, board1, move, board2):
        log.debug("Human.makeMove: move=%s, board1=%s board2=%s" % (
            move, board1, board2))
        if self.board.view.premove_piece and self.board.view.premove0 and \
                self.board.view.premove1 and \
                self.color == self.board.view.premove_piece.color:
            if validate(board1,
                        Move(self.board.view.premove0,
                             self.board.view.premove1,
                             board1,
                             promotion=self.board.view.premove_promotion)):
                log.debug("Human.makeMove: Setting move to premove %s %s" % (
                    self.board.view.premove0, self.board.view.premove1))
                self.board.emit_move_signal(
                    self.board.view.premove0,
                    self.board.view.premove1,
                    promotion=self.board.view.premove_promotion)
            # reset premove
            self.board.view.setPremove(None, None, None, None)
        self.gmwidg.setLocked(False)
        item = self.queue.get(block=True)
        self.gmwidg.setLocked(True)
        if item == "del":
            raise PlayerIsDead("Killed by foreign forces")
        if item == "int":
            log.debug("Human.makeMove: %s: raise TurnInterrupt" % self)
            raise TurnInterrupt
        return item

    # Ending the game

    def end(self, status, reason):
        self.queue.put("del")

    def kill(self, reason):
        print("I am killed", self)
        for num in self.conid:
            if self.board.handler_is_connected(num):
                self.board.disconnect(num)
        self.queue.put("del")

    # Interacting with the player

    @idle_add
    def hurry(self):
        title = _("Your opponent asks you to hurry!")
        text = _(
            "Generally this means nothing, as the game is time-based, but if you want to \
            please your opponent, perhaps you should get going.")
        content = InfoBar.get_message_content(title, text,
                                              Gtk.STOCK_DIALOG_INFO)

        def response_cb(infobar, response, message):
            message.dismiss()

        message = InfoBarMessage(Gtk.MessageType.INFO, content, response_cb)
        message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                Gtk.ResponseType.CANCEL))
        self.gmwidg.showMessage(message)

    def pause(self):
        self.gmwidg.setLocked(True)

    def resume(self):
        log.debug("Human.resume: %s" % (self))
        if self.board.view.model.curplayer == self:
            self.gmwidg.setLocked(False)

    def playerUndoMoves(self, movecount, gamemodel):
        log.debug("Human.playerUndoMoves:  movecount=%s self=%s" %
                  (movecount, self))
        # If the movecount is odd, the player has changed, and we have to interupt
        if movecount % 2 == 1:
            # If it is no longer us to move, we raise TurnInterruprt in order to
            # let GameModel continue the game.
            if gamemodel.curplayer != self:
                log.debug(
                    "Human.playerUndoMoves: putting TurnInterrupt into self.queue")
                self.queue.put("int")

        # If the movecount is even, we have to ensure the board is unlocked.
        # This is because it might have been locked by the game ending, but
        # perhaps we have now undone some moves, and it is no longer ended.
        elif movecount % 2 == 0 and gamemodel.curplayer == self:
            log.debug(
                "Human.playerUndoMoves: self=%s: calling gmwidg.setLocked" %
                (self))
            self.gmwidg.setLocked(False)

    def putMessage(self, text):
        self.emit("messageReceived", text)

    def sendMessage(self, text):
        self.emit("offer", Offer(CHAT_ACTION, param=text))

    # Offer handling

    @idle_add
    def offer(self, offer):
        log.debug("Human.offer: self=%s %s" % (self, offer))
        assert offer.type in OFFER_MESSAGES

        if self.gamemodel.players[1 - self.color].__type__ is LOCAL:
            self.emit("accept", offer)
            return

        heading, text, takes_param = OFFER_MESSAGES[offer.type]
        if takes_param:
            param = offer.param
            if offer.type == TAKEBACK_OFFER and \
                    self.gamemodel.players[1 - self.color].__type__ != REMOTE:
                param = self.gamemodel.ply - offer.param
            heading = heading % param
            text = text % param

        def response_cb(infobar, response, message):
            if response == Gtk.ResponseType.ACCEPT:
                self.emit("accept", offer)
            elif response == Gtk.ResponseType.NO:
                self.emit("decline", offer)
            message.dismiss()

        content = InfoBar.get_message_content(heading, text,
                                              Gtk.STOCK_DIALOG_QUESTION)
        message = InfoBarMessage(Gtk.MessageType.QUESTION, content,
                                 response_cb)
        message.add_button(InfoBarMessageButton(
            _("Accept"), Gtk.ResponseType.ACCEPT))
        message.add_button(InfoBarMessageButton(
            _("Decline"), Gtk.ResponseType.NO))
        message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                Gtk.ResponseType.CANCEL))
        self.gmwidg.showMessage(message)

    @idle_add
    def offerDeclined(self, offer):
        log.debug("Human.offerDeclined: self=%s %s" % (self, offer))
        assert offer.type in ACTION_NAMES
        heading = _("%s was declined by your opponent") % ACTION_NAMES[
            offer.type]
        text = _("Resend %s?" % ACTION_NAMES[offer.type].lower())
        content = InfoBar.get_message_content(heading, text,
                                              Gtk.STOCK_DIALOG_INFO)

        def response_cb(infobar, response, message):
            if response == Gtk.ResponseType.ACCEPT:
                self.emit("offer", offer)
            message.dismiss()

        message = InfoBarMessage(Gtk.MessageType.INFO, content, response_cb)
        message.add_button(InfoBarMessageButton(
            _("Resend"), Gtk.ResponseType.ACCEPT))
        message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                Gtk.ResponseType.CANCEL))
        self.gmwidg.showMessage(message)

    @idle_add
    def offerWithdrawn(self, offer):
        log.debug("Human.offerWithdrawn: self=%s %s" % (self, offer))
        assert offer.type in ACTION_NAMES
        heading = _("%s was withdrawn by your opponent") % ACTION_NAMES[
            offer.type]
        text = _("Your opponent seems to have changed their mind.")
        content = InfoBar.get_message_content(heading, text,
                                              Gtk.STOCK_DIALOG_INFO)

        def response_cb(infobar, response, message):
            message.dismiss()

        message = InfoBarMessage(Gtk.MessageType.INFO, content, response_cb)
        message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                Gtk.ResponseType.CANCEL))
        self.gmwidg.showMessage(message)

    @idle_add
    def offerError(self, offer, error):
        log.debug("Human.offerError: self=%s error=%s %s" %
                  (self, error, offer))
        assert offer.type in ACTION_NAMES
        actionName = ACTION_NAMES[offer.type]
        if error == ACTION_ERROR_NONE_TO_ACCEPT:
            heading = _("Unable to accept %s") % actionName.lower()
            text = _("Probably because it has been withdrawn.")
        elif error == ACTION_ERROR_NONE_TO_DECLINE or \
                error == ACTION_ERROR_NONE_TO_WITHDRAW:
            # If the offer was not there, it has probably already been either
            # declined or withdrawn.
            return
        else:
            heading = _("%s returns an error") % actionName
            text = ERROR_MESSAGES[error]

        content = InfoBar.get_message_content(heading, text,
                                              Gtk.STOCK_DIALOG_WARNING)

        def response_cb(infobar, response, message):
            message.dismiss()

        message = InfoBarMessage(Gtk.MessageType.WARNING, content, response_cb)
        message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                Gtk.ResponseType.CANCEL))
        self.gmwidg.showMessage(message)

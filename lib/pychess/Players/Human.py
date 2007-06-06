import gtk

from threading import Condition
from gobject import GObject
from Queue import Queue

from Player import Player, PlayerIsDead
from pychess.Utils.const import *

class Human (Player):
    __type__ = LOCAL
    
    def __init__ (self, board, color):
        GObject.__init__(self)
        
        self.gamemodel = board.view.model
        self.queue = Queue()
        self.color = color
        self.board = board
        self.conid = [
            board.connect("piece_moved", self.piece_moved),
            board.connect("call_flag", lambda b: self.emit_action(FLAG_CALL)),
            board.connect("draw", lambda b: self.emit_action(DRAW_OFFER)),
            board.connect("resign", lambda b: self.emit_action(RESIGNATION))
        ]
        self.name = "Human"
    
    def piece_moved (self, board, move):
        if self.gamemodel.boards[-1].color != self.color:
            return
        self.queue.put(move)
    
    def emit_action (self, action):
        if self.gamemodel.boards[-1].color != self.color:
            return
        self.emit("action", action, 0)
    
    def makeMove (self, gamemodel):
        self.board.locked = False
        item = self.queue.get(block=True)
        
        self.board.locked = True
        if item == "del":
            raise PlayerIsDead
        
        return item
    
    def _offer (self, action, param, title, description):
        d = gtk.MessageDialog (
                type = gtk.MESSAGE_QUESTION, buttons = gtk.BUTTONS_YES_NO)
        d.set_markup (title)
        d.format_secondary_text (description)
        def response (dialog, response):
            if response == gtk.RESPONSE_YES:
                self.emit("action", action, param)
            d.hide()
        d.connect("response", response)
        d.show_all()
    
    def offerDraw (self):
        self._offer ( DRAW_OFFER, 0,
                _("<big><b>You've got a draw offer. Accept?</b></big>"),
                _("Your opponent has offered you a draw. If you accept it the "+
                  "game will end with score 1/2 - 1/2.")
        )
    
    def offerAbort (self):
        self._offer ( ABORT_OFFER, 0,
                _("<big><b>You've got an abort offer. Accept?</b></big>"),
                _("Your opponent has offered you to abort the game. If you "+
                  "accept, the game will end with no rating change.")
        )
    
    def offerAdjourn (self):
        self._offer ( ADJOURN_OFFER, 0,
                _("<big><b>You've got an adjourn offer. Accept?</b></big>"),
                _("Your opponent has offered you to adjourn the game. If you "+
                  "accept, the game will adjourned, and you can later resume "+
                  "it (If your opponent is online and willing).")
        )
    
    def offerTakeback (self, toPly):
        self._offer ( TAKEBACK_OFFER, toPly,
                _("<big><b>Your opponent wants to undo. Accept?</b></big>"),
                _("Your opponent wants to undo back to halfmove %s.. If you "+
                  "accept, the game will continue from the earlier position.")
        )
    
    def setName (self, name):
        self.name = name
    
    def __repr__ (self):
        #TODO: Get name from preferences or accountname
        #(probably preferences, as accountname would give problems in pvp games)
        return self.name
    
    def kill (self, status, reason):
        for id in self.conid:
            if self.board.handler_is_connected(id):
                self.board.disconnect(id)
        self.queue.put("del")
    
    def setBoard (self, fen):
        # BoardControl, from which we are reciving moves, will be set by others
        pass

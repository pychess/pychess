import gtk

from threading import Condition
from gobject import GObject

from Player import Player
#TODO: This should be PlayerDead or something
from Engine import EngineDead

class Human (Player):
    def __init__ (self, board, color):
        GObject.__init__(self)
        
        self.move = None
        self.history = board.view.history
        self.cond = Condition()
        self.color = color
        self.board = board
        self.conid = [board.connect("piece_moved", self.piece_moved)]
        self.conid.append(board.connect("call_flag", lambda b: self.emit_action(self.FLAG_CALL)))
        self.conid.append(board.connect("draw", lambda b: self.emit_action(self.DRAW_OFFER)))
        self.conid.append(board.connect("resign", lambda b: self.emit_action(self.RESIGNATION)))
        self.name = "Human"
    
    def piece_moved (self, board, move):
        if self.history.curCol() != self.color:
            return
        self.cond.acquire()
        self.move = move
        self.cond.notify()
        self.cond.release()
    
    def emit_action (self, action):
        if self.history.curCol() != self.color:
            return
        self.emit("action", action)
    
    def makeMove (self, history):
        self.board.locked = False
        self.cond.acquire()
        while not self.move:
            self.cond.wait()
        self.board.locked = True
        if self.move == "del":
            self.cond.release()
            raise EngineDead
        move = self.move
        self.move = None
        self.cond.release()
        return move

    def offerDraw (self):
        d = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO)
        d.set_markup(_("<big><b>You've got a draw offer. Accept?</b></big>"))
        d.format_secondary_text(_("Your opponent has offered you a draw. If you accept it the game will end with score 1/2 - 1/2."))
        result = d.run()
        d.hide()
        if result == gtk.RESPONSE_YES:
            self.emit("action", self.DRAW_ACCEPTION)

    def setName (self, name):
        self.name = name

    def __repr__ (self):
        #TODO: Get name from preferences or accountname
        #(probably preferences, as accountname would give problems in pvp games)
        return self.name

    def __del__ (self):
        self.cond.acquire()
        for id in self.conid:
            if self.board.handler_is_connected(id):
                self.board.disconnect(id)
        self.move = "del"
        self.cond.notify()
        self.cond.release()

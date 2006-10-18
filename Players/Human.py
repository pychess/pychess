from threading import Condition
from gobject import GObject

from Player import Player
#TODO: This should be PlayerDead or something
from Engine import EngineDead

#http://linuxgazette.net/107/pai.html

class Human (Player):
    def __init__ (self, board, pnum):
        GObject.__init__(self)
        
        self.cond = Condition()
        self.pnum = pnum
        self.board = board
        self.conid = board.connect("piece_moved", self.piece_moved)
        self.name = "Human"
    
    move = None
    def piece_moved (self, board, move):
        if (len(board.view.history)-1) % 2 != self.pnum:
            return
        self.cond.acquire()
        self.move = move
        self.cond.notify()
        self.cond.release()
    
    def makeMove (self, history):
        self.board.locked = False
        self.cond.acquire()
        while not self.move:
            self.cond.wait()
        if self.move == "k":
            raise EngineDead
        move = self.move
        self.move = None
        self.cond.release()
        self.board.locked = True
        return move

    def setName (self, name):
        self.name = name

    def __repr__ (self):
        #TODO: Get name from preferences or accountname
        #(probably preferences, as accountname would give problems in pvp games)
        return self.name

    def __del__ (self):
        self.cond.acquire()
        if self.board.handler_is_connected(self.conid):
            self.board.disconnect(self.conid)
        self.move = "k"
        self.cond.notify()
        self.cond.release()

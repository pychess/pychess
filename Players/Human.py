from threading import Condition
from Player import Player

#http://linuxgazette.net/107/pai.html

class Human (Player):
    def __init__ (self, board, pnum):
        self.cond = Condition()
        self.pnum = pnum
        self.board = board
        self.conid = board.connect("piece_moved", self.piece_moved)
    
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
        move = self.move
        self.move = None
        self.cond.release()
        self.board.locked = True
        return move

    def __repr__ (self):
        #TODO: Get name from preferences or accountname
        #(probably preferences, as accountname would give problems in pvp games)
        return "Human"

    def __del__ (self):
        try:
            self.board.disconnect(self.conid)
        except: pass

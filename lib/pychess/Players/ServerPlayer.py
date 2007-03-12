
from Player import Player
from Player import PlayerIsDead
from Queue import Queue
from pychess.Utils.Move import parseSAN
from pychess.Utils.const import REMOTE

class ServerPlayer (Player):
    __type__ = REMOTE
    
    def __init__ (self, boardmanager, gameno, color):
        Player.__init__(self)
        
        self.queue = Queue()
        
        self.color = color
        self.gameno = gameno
        self.boardmanager = boardmanager
        self.boardmanager.connect("moveRecieved", self.moveRecieved)
        #...
    
    def moveRecieved (self, bm, fen, sanmove, gameno, curcol):
        if curcol != self.color or gameno != self.gameno:
            return
        print sanmove
        self.queue.put(sanmove)
    
    def makeMove (self, gamemodel):
        sanmove = self.queue.get(block=True)
        if sanmove == "del":
            raise PlayerIsDead
        move = parseSAN (gamemodel.boards[-1], sanmove)
        return move
    
    def __repr__ (self):
        #return self.boardmanager.getName(self.color)
        return "FICSPlayer"
    
    def setBoard (self, fen):
        # setBoard will currently only be called for ServerPlayer when starting
        # to observe some game. In this case FICS already knows how the board
        # should look, and we don't need to set anything
        pass
    
    def kill (self):
        self.boardmanager.resign()
        self.queue.put("del")

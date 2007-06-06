
from Queue import Queue

from Player import Player, PlayerIsDead
from pychess.Utils.Move import parseSAN, toSAN, ParsingError
from pychess.Utils.const import *
from pychess.ic import telnet

class ServerPlayer (Player):
    __type__ = REMOTE
    
    def __init__ (self, boardmanager, offermanager,
                        name, external, gameno, color):
        Player.__init__(self)
        
        self.queue = Queue()
        
        self.name = name
        # If we are not playing against a player on the users computer. E.g.
        # when we observe a game on FICS. In these cases we don't send anything
        # back to the server.
        self.external = external 
        self.color = color
        self.gameno = gameno
        
        self.boardmanager = boardmanager
        self.boardmanager.connect("moveRecieved", self.moveRecieved)
        self.offermanager = offermanager
        self.offermanager.connect("onOfferAdd", self.onOfferAdd)
        self.offermanager.connect("onOfferRemove", self.onOfferRemove)
        
        self.lastPly = -1
    
    def onOfferAdd (self, om, index, type, params):
        if type == "draw":
            self.emit ("action", DRAW_OFFER, 0)
            
        elif type == "abort":
            self.emit ("action", ABORT_OFFER, 0)
            
        elif type ==  "adjourn":
            self.emit ("action", ADJOURN_OFFER, 0)
            
        elif type == "takeback":
            toPly = self.lastPly - int(params)
            self.emit ("action", TAKEBACK_OFFER, toPly)
    
    def onOfferRemove (self, om, index):
        pass
    
    def offerDraw (self):
        print >> telnet.client, "draw"
    
    def offerAbort (self):
        print >> telnet.client, "abort"
    
    def offerAdjourn (self):
        print >> telnet.client, "adjourn"
    
    def offerTakeback (self, toPly):
        print >> telnet.clinet, "takeback", toPly
    
    def moveRecieved (self, bm, ply, sanmove, gameno, curcol):
        if curcol != self.color or gameno != self.gameno:
            return
        print sanmove
        self.queue.put((ply,sanmove))
    
    def pause (self):
        pass
    
    def resume (self):
        pass
    
    def makeMove (self, gamemodel):
        if gamemodel.moves and not self.external:
            self.boardmanager.sendMove (
                    toSAN (gamemodel.boards[-2], gamemodel.moves[-1]))
        
        item = self.queue.get(block=True)
        if item == "del":
            raise PlayerIsDead
        
        ply, sanmove = item
        if ply < gamemodel.ply:
            # This should only happen in an observed game
            self.emit("action", (TAKEBACK_FORCE, ply))
        
        try:
            move = parseSAN (gamemodel.boards[-1], sanmove)
        except ParsingError, e:
            print "Error", e.args[0]
            raise PlayerIsDead
        return move
    
    def __repr__ (self):
        return self.name
    
    def setBoard (self, fen):
        # setBoard will currently only be called for ServerPlayer when starting
        # to observe some game. In this case FICS already knows how the board
        # should look, and we don't need to set anything
        pass
    
    def kill (self, status, reason):
        if reason == WON_RESIGN:
            if self.color == WHITE and status == WHITEWON or \
                    self.color == BLACK and status == BLACKWON:
                self.boardmanager.resign()
        
        if reason == DRAW_CALLFLAG:
            self.boardmanager.callflag()
        
        self.queue.put("del")

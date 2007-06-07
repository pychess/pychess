
from pychess.Utils.GameModel import GameModel
from pychess.Utils.const import REMOTE

class IcGameModel (GameModel):
    
    def __init__ (self, boardmanager, gameno, timemodel):
        GameModel.__init__(self, timemodel)
        self.boardmanager = boardmanager
        self.gameno = gameno
        
        boardmanager.connect("clockUpdatedMs", self.onClockUpdatedMs)
        boardmanager.connect("boardRecieved", self.onBoardRecieved)
        boardmanager.connect("gameEnded", self.onGameEnded)
        boardmanager.connect("gamePaused", self.onGamePaused)
        
        self.inControl = True
    
    def onClockUpdatedMs (self, boardmanager, gameno, msecs, color):
        if gameno == self.gameno:
            self.timemodel.updatePlayer (color, msecs/1000.)
    
    def onBoardRecieved (self, boardmanager, gameno, ply, fen, wsecs, bsecs):
        if gameno == self.gameno:
            print "SYNC CLOCK", wsecs, bsecs
            self.timemodel.syncClock (wsecs, bsecs)
            if ply < self.ply:
                print "TAKEBACK", self.ply, ply
                for i in range(ply, self.ply):
                    self.undo()
    
    def onGameEnded (self, boardmanager, gameno, status, reason):
        if gameno == self.gameno:
            self.end (status, reason)
    
    def setPlayers (self, players):
        if [player.__type__ for player in players] == [REMOTE, REMOTE]:
            self.inControl = False
        GameModel.setPlayers (self, players)
    
    def onGamePaused (self, boardmanager, gameno, paused):
        if paused:
            self.pause()
        else: self.resume()

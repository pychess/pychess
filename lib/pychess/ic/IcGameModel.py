
from pychess.Utils.GameModel import GameModel
from pychess.Utils.const import REMOTE

class IcGameModel (GameModel):
    
    def __init__ (self, boardmanager, gameno, timemodel):
        GameModel.__init__(self, timemodel)
        self.boardmanager = boardmanager
        self.gameno = gameno
        
        boardmanager.connect("clockUpdatedMs", self.onClockUpdatedMs)
        boardmanager.connect("clockUpdated", self.onClockUpdated)
        boardmanager.connect("gameEnded", self.onGameEnded)
        
        self.inControl = True
    
    def onClockUpdatedMs (self, boardmanager, gameno, msecs, color):
        if gameno == self.gameno:
            self.timemodel.updatePlayer (color, msecs/1000.)
    
    def onClockUpdated (self, boardmanager, gameno, wsecs, bsecs):
        if gameno == self.gameno:
            self.timemodel.syncTime (wsecs, bsecs)
    
    def onGameEnded (self, boardmanager, gameno, status, reason):
        if gameno == self.gameno:
            self.forceStatus (status, reason)
    
    def setPlayers (self, players):
        if [player.__type__ for player in players] == [REMOTE, REMOTE]:
            self.inControl = False
        GameModel.setPlayers (self, players)

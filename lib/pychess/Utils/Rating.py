import gobject
from pychess.ic import *

class Rating (gobject.GObject):
    def __init__(self, ratingtype, elo, deviation=DEVIATION_NONE, wins=0,
                 losses=0, draws=0, bestElo=0, bestTime=0):
        gobject.GObject.__init__(self)
        self.type = ratingtype
        for v in (elo, deviation, wins, losses, draws, bestElo, bestTime):
            assert v == None or type(v) == int, v
        self.elo = elo
        self.deviation = deviation
        self.wins = wins
        self.losses = losses
        self.draws = draws
        self.bestElo = bestElo
        self.bestTime = bestTime
    
    def get_elo (self):
        return self._elo
    def set_elo (self, elo):
        assert type(elo) == int, type(elo)
        self._elo = elo
    elo = gobject.property(get_elo, set_elo)
    
    def __repr__ (self):
        r = "type=%s, elo=%s" % (self.type, self.elo)
        if self.deviation != None:
            r += ", deviation=%s" % str(self.deviation)
        if self.wins > 0:
            r += ", wins=%s" % str(self.wins)
        if self.losses > 0:
            r += ", losses=%s" % str(self.losses)
        if self.draws > 0:
            r += ", draws=%s" % str(self.draws)
        if self.bestElo > 0:
            r += ", bestElo=%s" % str(self.bestElo)
        if self.bestTime > 0:
            r += ", bestTime=%s" % str(self.bestTime)
        return "<Rating " + r + ">"
    
    def copy (self):
        return Rating(self.type, self.elo, deviation=self.deviation,
            wins=self.wins, losses=self.losses, draws=self.draws,
            bestElo=self.bestElo, bestTime=self.bestTime)
        
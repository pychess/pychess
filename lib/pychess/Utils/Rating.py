from pychess.Utils.const import *

class Rating (object):
    def __init__(self, ratingtype, elo, deviation = None, wins = 0, losses = 0,
                                  draws = 0, bestElo = 0, bestTime = 0):
        self.type = ratingtype
        for v in (elo, deviation, wins, losses, draws, bestElo, bestTime):
            assert v == None or type(v) == type(0), v
        self.elo = elo
        self.deviation = deviation
        self.wins = wins
        self.losses = losses
        self.draws = draws
        self.bestElo = bestElo
        self.bestTime = bestTime
    
    def update (self, rating):
        if self.type != rating.type:
            raise
        elif self.elo != rating.elo:
            self.elo = rating.elo
        elif rating.deviation != None and self.deviation != rating.deviation:
            self.deviation = rating.deviation
        elif rating.wins > 0 and self.wins != rating.wins:
            self.wins = rating.wins
        elif rating.losses > 0 and self.losses != rating.losses:
            self.losses = rating.losses
        elif rating.draws > 0 and self.draws != rating.draws:
            self.draws = rating.draws
        elif rating.bestElo > 0 and self.bestElo != rating.bestElo:
            self.bestElo = rating.bestElo
        elif rating.bestTime > 0 and self.bestTime != rating.bestTime:
            self.bestTime = rating.bestTime
    
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
        return r

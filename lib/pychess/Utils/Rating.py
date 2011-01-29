class Rating:
    def __init__(self, type, elo, deviation = 0, wins = 0, losses = 0,
                                  draws = 0, bestElo = 0, bestTime = 0):
        self.type = type
        self.elo = elo
        self.deviation = deviation
        self.wins = wins
        self.losses = losses
        self.draws = draws
        self.bestElo = bestElo
        self.bestTime = bestTime

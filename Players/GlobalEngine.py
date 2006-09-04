from Player import Player

class Engine (Player):
    def newGame (self, color, strength, (hours, minutes, seconds, plus)):
        """Takes a color (-1: human vs. human, 0: white, 1: black),
           a strength 0 - 2 (higher is better)
           and a time tupple to init the engine"""
        abstract
    
    def setStrength (self, strength):
        """Takes strength 0 - 2 (higher is better)"""
        abstract
    
    def makeMove (history):
        """Returns a move, as an answer to the last move in history"""
        abstract
    
    def undoMoves (self, moves = 1):
        """Undos a number of moves."""
    
    # Methods usable in human vs. human enviroments
    
    def score (self):
        """Returns a score of opponents situation"""
        optional
    
    def getSpeed (self):
        """Returns a the number of moves, the engine calculates per second"""
        optional
        
    def hint (self):
        """Returns a hint to the opponent"""
        optional
    
    def book (self):
        """Returns a tuple of usable bookmoves"""
        optional
    
#    def possibleMoves (self):
#        """Returns a tuple of possible moves"""
#        optional
    
    # Other methods
    
    def testEngine (self):
        """Should raise an AssertionError, optionally with a location to get the engine,
        if the engine cannot be found"""
        abstract
    
    def __repr__ (self):
        """For example 'GNU Chess 5.07'"""
        abstract

import threading
from urllib import urlopen, urlencode

from gobject import SIGNAL_RUN_FIRST, TYPE_NONE

from pychess.System.ThreadPool import pool
from pychess.Utils.Offer import Offer
from pychess.Utils.const import ARTIFICIAL, DRAW_OFFER, CHAT_ACTION

from Player import Player

class Engine (Player):
    
    __type__ = ARTIFICIAL
    
    __gsignals__ = {
        'analyze': (SIGNAL_RUN_FIRST, TYPE_NONE, (object,))
    }
    
    def __init__(self):
        Player.__init__(self)
        
        self.currentAnalysis = []
        def on_analysis(self_, analysis):
            self.currentAnalysis = analysis
        self.connect('analyze', on_analysis)
    
    #===========================================================================
    #    Offer handling
    #===========================================================================
    
    def offer (self, offer):
        raise NotImplementedError
    
    def offerDeclined (self, offer):
        pass #Ignore
    
    def offerWithdrawn (self, offer):
        pass #Ignore
    
    def offerError (self, offer, error):
        pass #Ignore
    
    #===========================================================================
    #    General Engine Options
    #===========================================================================
    
    def setOptionAnalyzing (self, mode):
        self.mode = mode
    
    def setOptionInitialBoard (self, model):
        """ If the game starts at a board other than FEN_START, it should be
            sent here. We sends a gamemodel, so the engine can load the entire
            list of moves, if any """
        pass # Optional
    
    def setOptionVariant (self, variant):
        """ Inform the engine of any special variant. If the engine doesn't
            understand the variant, this will raise an error. """
        raise NotImplementedError
    
    def setOptionTime (self, secs, gain):
        """ Seconds is the initial clock of the game.
            Gain is the amount of seconds a player gets after each move.
            If the engine doesn't support playing with time, this will fail."""
        raise NotImplementedError
    
    def setOptionStrength (self, strength):
        """ Strength is a number [1,8] inclusive. Higher is better. """
        raise NotImplementedError
    
    #===========================================================================
    #    Engine specific methods
    #===========================================================================
    
    def canAnalyze (self):
        raise NotImplementedError
    
    def analyze (self, model, inverse=False):
        """ If canAnalyze responds True, this method will be called on the
            engine, if it is not to play any moves, but rather analyze the game
            and emit 'analyze' signals now and then """
        #Optional
    
    def getAnalysis (self):
        """ Returns a list of moves, or None if there haven't yet been made an
            analysis """
        return self.currentAnalysis
    
    #===========================================================================
    #    General chat handling
    #===========================================================================
    
    def putMessage (self, message):
        def answer (message):
            data = urlopen("http://www.pandorabots.com/pandora/talk?botid=8d034368fe360895",
                           urlencode({"message":message, "botcust2":"x"})).read()
            ss = "<b>DMPGirl:</b>"
            es = "<br>"
            answer = data[data.find(ss)+len(ss) : data.find(es,data.find(ss))]
            self.emit("offer", Offer(CHAT_ACTION, answer))
        pool.start(answer)

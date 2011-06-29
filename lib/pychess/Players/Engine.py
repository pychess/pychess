import threading
from urllib import urlopen, urlencode

from gobject import SIGNAL_RUN_FIRST, TYPE_NONE

from pychess.System.ThreadPool import pool
from pychess.System.Log import log
from pychess.Utils.Offer import Offer
from pychess.Utils.const import ARTIFICIAL, DRAW_OFFER, CHAT_ACTION


from Player import Player

class Engine (Player):
    
    __type__ = ARTIFICIAL
    
    ''' The first argument is the pv list of moves. The second is a score
        relative to the engine. If no score is known, the value can be None,
        but not 0, which is a draw. '''
    __gsignals__ = {
        'analyze': (SIGNAL_RUN_FIRST, TYPE_NONE, (object,object))
    }
    
    def __init__(self):
        Player.__init__(self)
        
        self.currentAnalysis = []
        def on_analysis(self_, analysis, score):
            if score != None:
                self.currentScore = score
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
        self.strength = strength
        raise NotImplementedError
    
    #===========================================================================
    #    Engine specific methods
    #===========================================================================
    
    def canAnalyze (self):
        raise NotImplementedError
    
    def getAnalysis (self):
        """ Returns a list of moves, or None if there haven't yet been made an
            analysis """
        return self.currentAnalysis
    
    #===========================================================================
    #    General chat handling
    #===========================================================================
    
    def putMessage (self, message):
        def answer (message):
            try:
                data = urlopen("http://www.pandorabots.com/pandora/talk?botid=8d034368fe360895",
                               urlencode({"message":message, "botcust2":"x"})).read()
            except IOError, e:
                log.warn("Couldn't answer message from online bot: '%s'\n" % e,
                         self.defname)
                return
            ss = "<b>DMPGirl:</b>"
            es = "<br>"
            answer = data[data.find(ss)+len(ss) : data.find(es,data.find(ss))]
            self.emit("offer", Offer(CHAT_ACTION, answer))
        pool.start(answer, message)

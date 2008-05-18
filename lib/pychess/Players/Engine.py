import threading
from urllib import urlopen, urlencode

from gobject import SIGNAL_RUN_FIRST, TYPE_NONE

from pychess.Utils.Offer import Offer
from pychess.Utils.const import ARTIFICIAL, DRAW_OFFER, CHAT_ACTION
from Player import Player

class Engine (Player):
    
    __type__ = ARTIFICIAL
    
    __gsignals__ = {
        'analyze': (SIGNAL_RUN_FIRST, TYPE_NONE, (object,))
    }
    
    def setStrength (self, strength):
        """ Takes strength 0, 1, 2 (higher is better) """
        #Optional
    
    def setDepth (self, depth):
        """ Sets the depth of the engine. Should only be used for analyze engines.
            Other engines will use the setStrength method. """
        #Optional
    
    def setTime (self, seconds, gain):
        raise NotImplementedError
    
    def setBoard (self, history):
        raise NotImplementedError
    
    def wait (self):
        """ Will block until engine is ready """
        raise NotImplementedError
    
    def canAnalyze (self):
        raise NotImplementedError
    
    def analyze (self, inverse=False):
        """ If canAnalyze responds True, this method will be called on the
            engine, if it is not to play any moves, but rather analyze the game
            and emit 'analyze' signals now and then """
        #Optional
    
    def offer (self, offer):
        raise NotImplementedError
    
    def offerDeclined (self, offer):
        pass #Ignore
    
    def offerWithdrawn (self, offer):
        pass #Ignore
    
    def offerError (self, offer, error):
        pass #Ignore
    
    def putMessage (self, message):
        thread = threading.Thread(target=self.answer, args=(message,))
        thread.start()
    
    def answer (self, message):
        data = urlopen("http://www.pandorabots.com/pandora/talk?botid=8d034368fe360895",
                       urlencode({"message":message, "botcust2":"x"})).read()
        ss = "<b>DMPGirl:</b>"
        es = "<br>"
        answer = data[data.find(ss)+len(ss) : data.find(es,data.find(ss))]
        self.emit("offer", Offer(CHAT_ACTION, answer))
    
    # Other methods
    
    def __repr__ (self):
        """For example 'GNU Chess 5.07'"""
        raise NotImplementedError

from __future__ import absolute_import

from threading import Thread
from gi.repository import GObject


from pychess.compat import urlopen, urlencode
from pychess.System import fident
from pychess.System.Log import log
from pychess.Utils.Offer import Offer
from pychess.Utils.const import ARTIFICIAL, CHAT_ACTION

from .Player import Player


class Engine(Player):

    __type__ = ARTIFICIAL
    ''' Argument is a vector of analysis lines.
        The first element is the pv list of moves. The second is a score
        relative to the engine. If no score is known, the value can be None,
        but not 0, which is a draw. '''
    __gsignals__ = {
        'analyze': (GObject.SignalFlags.RUN_FIRST, None, (object, ))
    }

    def __init__(self, md5=None):
        Player.__init__(self)
        self.md5 = md5
        self.currentAnalysis = []
        self.analyze_cid = self.connect('analyze', self.on_analysis)

    def on_analysis(self, engine, analysis):
        self.currentAnalysis = analysis

    # Offer handling

    def offer(self, offer):
        raise NotImplementedError

    def offerDeclined(self, offer):
        pass  # Ignore

    def offerWithdrawn(self, offer):
        pass  # Ignore

    def offerError(self, offer, error):
        pass  # Ignore

    # General Engine Options

    def setOptionAnalyzing(self, mode):
        self.mode = mode

    def setOptionInitialBoard(self, model):
        """ If the game starts at a board other than FEN_START, it should be
            sent here. We sends a gamemodel, so the engine can load the entire
            list of moves, if any """
        pass  # Optional

    def setOptionVariant(self, variant):
        """ Inform the engine of any special variant. If the engine doesn't
            understand the variant, this will raise an error. """
        raise NotImplementedError

    def setOptionTime(self, secs, gain):
        """ Seconds is the initial clock of the game.
            Gain is the amount of seconds a player gets after each move.
            If the engine doesn't support playing with time, this will fail."""
        raise NotImplementedError

    def setOptionStrength(self, strength):
        """ Strength is a number [1,8] inclusive. Higher is better. """
        self.strength = strength
        raise NotImplementedError

    # Engine specific methods

    def canAnalyze(self):
        raise NotImplementedError

    def maxAnalysisLines(self):
        raise NotImplementedError

    def requestMultiPV(self, setting):
        """Set the number of analysis lines the engine will give, if possible.

        If setting is too high, the engine's maximum will be used.
        The setting will last until the next call to requestMultiPV.
        Return value: the setting used.
        """
        raise NotImplementedError

    def getAnalysis(self):
        """ Returns a list of moves, or None if there haven't yet been made an
            analysis """
        return self.currentAnalysis

    # General chat handling

    def putMessage(self, message):
        def answer(message):
            try:
                data = urlopen(
                    "http://www.pandorabots.com/pandora/talk?botid=8d034368fe360895",
                    urlencode({"message": message,
                               "botcust2": "x"}).encode("utf-8")).read().decode('utf-8')
            except IOError as err:
                log.warning("Couldn't answer message from online bot: '%s'" %
                            err,
                            extra={"task": self.defname})
                return
            sstring = "<b>DMPGirl:</b>"
            estring = "<br>"
            answer = data[data.find(sstring) + len(sstring):data.find(estring, data.find(sstring))]
            self.emit("offer", Offer(CHAT_ACTION, answer))

        thread = Thread(target=answer, name=fident(answer), args=(message, ))
        thread.daemon = True
        thread.start()

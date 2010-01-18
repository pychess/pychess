import unittest

from pychess.Utils.const import WHITE, ANALYZING, INVERSE_ANALYZING
from pychess.Utils.lutils.ldata import MATE_VALUE
from pychess.Utils.Move import listToMoves
from pychess.Utils.Cord import Cord
from pychess.Utils.Board import Board
from pychess.Players.CECPEngine import CECPEngine

from Queue import Queue

from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

class DummyCECPAnalyzerEngine(GObject):
    __gsignals__ = {
        "line": (SIGNAL_RUN_FIRST, None, (object,)),
        "died": (SIGNAL_RUN_FIRST, None, ()),
    }
    def __init__(self):
        GObject.__init__(self)
        self.defname = 'Dummy'
        self.Q = Queue()
    def putline(self, line):
        self.emit('line', [line])
    def write(self, text):
        if text.strip() == 'protover 2':
            self.emit('line', ['feature setboard=1 analyze=1 ping=1 draw=0 sigint=0 done=1'])
        pass
    def readline(self):
        return self.Q.get()

class EmittingTestCase(unittest.TestCase):
    def __init__ (self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        self.args = {}
    def traceSignal(self, object, signal):
        self.args[object] = None
        def handler(manager, *args):
            self.args[object] = args
        object.connect(signal, handler)
    def getSignalResults(self, object):
        return self.args.get(object, None)
    
class CECPTests(EmittingTestCase):
    
    def _setupengine(self, mode):
        engine = DummyCECPAnalyzerEngine()
        analyzer = CECPEngine(engine, WHITE, 2)
        def optionsCallback (engine):
            analyzer.setOptionAnalyzing(mode)
        analyzer.connect("readyForOptions", optionsCallback)
        analyzer.prestart()
        analyzer.start()
        return engine, analyzer
    
    def setUp (self):
        self.engineA, self.analyzerA = self._setupengine(ANALYZING)
        self.engineI, self.analyzerI = self._setupengine(INVERSE_ANALYZING)
    
    def test1(self):
        """ Test analyzing in forced mate situations """
        
        board = Board('B1n1n1KR/1r5B/6R1/2b1p1p1/2P1k1P1/1p2P2p/1P2P2P/3N1N2 w - - 0 1')
        self.analyzerA.setBoard([board],[])
        self.analyzerI.setBoard([board],[])
        
        self.traceSignal(self.analyzerA, 'analyze')
        self.engineA.putline("1. Mat1 0 1     Bxb7#")
        results = self.getSignalResults(self.analyzerA)
        self.assertNotEqual(results, None, "signal wasn't sent")
        self.assertEqual(results, (listToMoves(board,['Bxb7#']), MATE_VALUE-1))
        
        # Notice, in the opposite situation there is no forced mate. Black can
        # do Bxe3 or Ne7+, but we just emulate a stupid analyzer not
        # recognizing this.
        self.traceSignal(self.analyzerI, 'analyze')
        self.engineI.putline("10. -Mat 2 35 64989837     Bd4 Bxb7#")
        results = self.getSignalResults(self.analyzerI)
        self.assertNotEqual(results, None, "signal wasn't sent")
        self.assertEqual(results, (listToMoves(board.switchColor(),['Bd4','Bxb7#']), -MATE_VALUE+2))

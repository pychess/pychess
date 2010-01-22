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
    
    def _testLine(self, engine, analyzer, board, analine, moves, score):
        self.traceSignal(analyzer, 'analyze')
        engine.putline(analine)
        results = self.getSignalResults(analyzer)
        self.assertNotEqual(results, None, "signal wasn't sent")
        self.assertEqual(results, (listToMoves(board,moves), score))
    
    def setUp (self):
        self.engineA, self.analyzerA = self._setupengine(ANALYZING)
        self.engineI, self.analyzerI = self._setupengine(INVERSE_ANALYZING)
    
    def test1(self):
        """ Test analyzing in forced mate situations """
        
        board = Board('B1n1n1KR/1r5B/6R1/2b1p1p1/2P1k1P1/1p2P2p/1P2P2P/3N1N2 w - - 0 1')
        self.analyzerA.setBoard([board],[])
        self.analyzerI.setBoard([board],[])
        
        self._testLine(self.engineA, self.analyzerA, board,
                       "1. Mat1 0 1     Bxb7#",
                       ['Bxb7#'], MATE_VALUE-1)
        
        # Notice, in the opposite situation there is no forced mate. Black can
        # do Bxe3 or Ne7+, but we just emulate a stupid analyzer not
        # recognizing this.
        self._testLine(self.engineI, self.analyzerI, board.switchColor(),
                       "10. -Mat 2 35 64989837     Bd4 Bxb7#",
                       ['Bd4','Bxb7#'], -MATE_VALUE+2)
    
    def test2(self):
        """ Test analyzing in promotion situations """
        
        board = Board('5k2/PK6/8/8/8/6P1/6P1/8 w - - 1 48')
        self.analyzerA.setBoard([board],[])
        self.analyzerI.setBoard([board],[])
        
        self._testLine(self.engineA, self.analyzerA, board,
                       "9. 1833 23 43872584     a8=Q+ Kf7 Qa2+ Kf6 Qd2 Kf5 g4+",
                       ['a8=Q+','Kf7','Qa2+','Kf6','Qd2','Kf5','g4+'], 1833)
        
        self._testLine(self.engineI, self.analyzerI, board.switchColor(),
                       "10. -1883 59 107386433     Kf7 a8=Q Ke6 Qa6+ Ke5 Qd6+ Kf5",
                       ['Kf7','a8=Q','Ke6','Qa6+','Ke5','Qd6+','Kf5'], -1883)

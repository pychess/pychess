import unittest

import __builtin__
__builtin__.__dict__['_'] = lambda s: s

from pychess.Utils.const import WHITE
from pychess.ic.FICSConnection import Connection
from pychess.ic.VerboseTelnet import PredictionsTelnet
from pychess.ic.managers.AdjournManager import AdjournManager

from Queue import Queue

class DummyConnection(Connection):
    class DummyClient(PredictionsTelnet):
        class DummyTelnet():
            def __init__(self):
                self.Q = Queue()
            def putline(self, line):
                self.Q.put(line)
            def readline(self):
                return self.Q.get()
        
        def __init__(self):
            PredictionsTelnet.__init__(self, self.DummyTelnet())
        def putline(self, line):
            self.telnet.putline(line)
    
    def __init__(self):
        Connection.__init__(self, 'host', (0,), 'tester', '123456')
        self.client = self.DummyClient()
    def putline(self, line):
        self.client.putline(line)
    def handleSomeText(self):
        self.client.handleSomeText(self.predictions)

###############################################################################
# Adjourn manager
###############################################################################

class AdjournManagerTests(unittest.TestCase):
    
    def setUp (self):
        self.conn = DummyConnection()
        self.manager = AdjournManager(self.conn)
    
    def _testHelper(self, lines, signal, expectedResult):
        self.args = None
        def handler(manager, *args): self.args = args
        self.manager.connect(signal, handler)
        
        for line in lines:
            self.conn.putline(line)
            self.conn.handleSomeText()
        
        self.assertNotEqual(self.args, None, "%s signal wasn't sent" % signal)
        self.assertEqual(self.args[0], expectedResult) 
        
    
    def test1(self):
        """Testing an advanced line"""
        
        lines = ['    C Opponent       On Type          Str  M    ECO Date',
                 ' 1: W mgatto          N [ wr  2   2] 31-31 W18  --- Wed Dec 23, 06:58 PST 2009',
                 'fics% ']
        
        signal = 'onAdjournmentsList'
        
        expectedResult = [{"color":WHITE, "opponent":'mgatto', "online":False, "length":34,
                           "time":'12/23/2009 06:58', "minutes":2, "gain":2}]
        
        self._testHelper(lines, signal, expectedResult)
    
    
    def test2(self):
        """Testing a double line"""
        
        lines = ['    C Opponent       On Type          Str  M    ECO Date',
                 ' 1: W TheDane       N [ br  2  12]  0-0  B2   ??? Sun Nov 23,  6:14 CST 1997',
                 ' 2: W PyChess       Y [psu  2  12] 39-39 W3   C20 Sun Jan 11, 17:40 ??? 2009',
                 'fics% ']
        
        signal = 'onAdjournmentsList'
        
        expectedResult = [{"color":WHITE, "opponent":'TheDane', "online":False, "length":3,
                           "time":'11/23/1997 06:14', "minutes":2, "gain":12},
                          {"color":WHITE, "opponent":'PyChess', "online":True, "length":4,
                           "time":'01/11/2009 17:40', "minutes":2, "gain":12}]
        
        self._testHelper(lines, signal, expectedResult)

###############################################################################
# ... manager
###############################################################################

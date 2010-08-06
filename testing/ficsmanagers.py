import unittest

from pychess.Utils.const import WHITE
from pychess.ic.FICSConnection import Connection
from pychess.ic.VerboseTelnet import PredictionsTelnet
from pychess.ic.managers.AdjournManager import AdjournManager
from pychess.ic.managers.GameListManager import GameListManager
from pychess.ic.managers.ListAndVarManager import ListAndVarManager


from Queue import Queue

class DummyConnection(Connection):
    class DummyClient(PredictionsTelnet):
        class DummyTelnet():
            def __init__(self):
                self.Q = Queue()
            def putline(self, line):
                self.Q.put(line)
            def write(self, text):
                pass
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

class DummyVarManager:
    def setVariable (self, name, value):
        pass

class EmittingTestCase(unittest.TestCase):
    ''' Helps working with unittests on emitting objects.
        Warning: Strong connection to fics managers '''
    def runAndAssertEquals(self, signal, lines, expectedResults):
        self.args = None
        def handler(manager, *args): self.args = args
        self.manager.connect(signal, handler)
        
        for line in lines:
            self.conn.putline(line)
            self.conn.handleSomeText()
        
        self.assertNotEqual(self.args, None, "%s signal wasn't sent" % signal)
        self.assertEqual(self.args, expectedResults)

###############################################################################
# AdjournManager
###############################################################################

class AdjournManagerTests(EmittingTestCase):
    
    def setUp (self):
        self.conn = DummyConnection()
        self.manager = AdjournManager(self.conn)
    
    def test1(self):
        """Testing an advanced line"""
        
        signal = 'onAdjournmentsList'
        
        lines = ['    C Opponent       On Type          Str  M    ECO Date',
                 ' 1: W mgatto          N [ wr  2   2] 31-31 W18  --- Wed Dec 23, 06:58 PST 2009',
                 'fics% ']
        
        expectedResult = [{"color":WHITE, "opponent":'mgatto', "online":False, "length":34,
                           "time":'12/23/2009 06:58', "minutes":2, "gain":2}]
        
        self.runAndAssertEquals(signal, lines, (expectedResult,))
    
    
    def test2(self):
        """Testing a double line"""
        
        signal = 'onAdjournmentsList'
        
        lines = ['    C Opponent       On Type          Str  M    ECO Date',
                 ' 1: W TheDane       N [ br  2  12]  0-0  B2   ??? Sun Nov 23,  6:14 CST 1997',
                 ' 2: W PyChess       Y [psu  2  12] 39-39 W3   C20 Sun Jan 11, 17:40 ??? 2009',
                 'fics% ']
        
        expectedResult = [{"color":WHITE, "opponent":'TheDane', "online":False, "length":3,
                           "time":'11/23/1997 06:14', "minutes":2, "gain":12},
                          {"color":WHITE, "opponent":'PyChess', "online":True, "length":4,
                           "time":'01/11/2009 17:40', "minutes":2, "gain":12}]
        
        self.runAndAssertEquals(signal, lines, (expectedResult,))
    
    def test3(self):
        """ The case where player has no games in adjourned """
        
        self.runAndAssertEquals('onAdjournmentsList',
                                ['%s has no adjourned games.' % self.conn.username],
                                ([],))
    
    def test4(self):
        """ Test acquiring preview without adjournment list """
        
        signal = 'onGamePreview'
        
        lines = ['Move  PyChess            selman',
                 '----  ----------------   ----------------',
                 '  1.  e4      (0:00.000)     c5      (0:00.000)',  
                 '  2.  Nf3     (0:00.000) ',
                 '      {White lost connection; game adjourned} *',
                 'fics% ']
        
        expectedPgn = '[Event "Ficsgame"]\n[Site "Internet"]\n[White "PyChess"]\n[Black "selman"]\n'
        expectedPgn += '1. e4 c5 2. Nf3 *'
        
        # Notice: argument two and three (secs and gain) are set to the
        #         default (60, 0) values, as time is normally read from the
        #         adjournment list
        expectedResults = (expectedPgn, 60, 0, 'PyChess', 'selman')
        
        self.runAndAssertEquals(signal, lines, expectedResults)
    
    def test5(self):
        """ Test acquiring preview with adjournment list """
        
        signal = 'onGamePreview'
        
        lines = ['    C Opponent       On Type          Str  M    ECO Date',
                 ' 1: B PyChess         N [ bu  2  12] 39-39 W2   C20 Sun Jan 11, 11:25 PST 2009',
                 
                 'Move  PyChess            Lobais',  
                 '----  ----------------   ----------------',
                 '  1.  e4      (0:00)     e5      (0:00)  ',
                 '      {Game adjourned by mutual agreement} *']
        
        expectedPgn = '[Event "Ficsgame"]\n[Site "Internet"]\n[White "PyChess"]\n[Black "Lobais"]\n'
        expectedPgn += '1. e4 e5 *'
        
        # Notice: argument two and three (secs and gain) are set to the
        #         original game values. These are not likely the same as they
        #         wore, when the game was adjourned
        expectedResults = (expectedPgn, 120, 12, 'PyChess', 'Lobais')
        
        self.runAndAssertEquals(signal, lines, expectedResults)

###############################################################################
# GameListManager
###############################################################################

class GameListManagerTests(EmittingTestCase):
    
    def setUp (self):
        self.conn = DummyConnection()
        # The real one stucks
        #self.conn.lvm = ListAndVarManager(self.conn)
        self.conn.lvm = DummyVarManager()
        self.manager = GameListManager(self.conn)
    
    def test1 (self):
        """ Seek add """
        
        signal = 'addSeek'
        
        lines = ['<s> 10 w=warbly ti=00 rt=1291  t=3 i=0 r=r tp=blitz c=? rr=1200-1400 a=t f=t']
        expectedResult = {'gameno':'10', 'tp':_("Blitz"), 'rmin':'1200', 'rmax':'1400',
                          'cp':False, 'rt':'1291', 'manual':False,
                          'w':'warbly', 'r':'r', 't':'3', 'i':'0'}
        self.runAndAssertEquals(signal, lines, (expectedResult,))
        
        lines = ['<s> 124 w=leaderbeans ti=02 rt=1637E t=3 i=0 r=u tp=blitz c=B rr=0-9999 a=t f=f']
        expectedResult = {'gameno':'124', 'tp':_("Blitz"), 'rmin':'0', 'rmax':'9999',
                          'cp':True, 'rt':'1637', 'manual':False,
                          'w':'leaderbeans', 'r':'u', 't':'3', 'i':'0'}
        self.runAndAssertEquals(signal, lines, (expectedResult,))

        lines = ['<s> 14 w=microknight ti=00 rt=1294  t=15 i=0 r=u tp=standard c=? rr=1100-1450 a=f f=f']
        expectedResult = {'gameno':'14', 'tp':_("Standard"), 'rmin':'1100', 'rmax':'1450',
                          'cp':False, 'rt':'1294', 'manual':True,
                          'w':'microknight', 'r':'u', 't':'15', 'i':'0'}
        self.runAndAssertEquals(signal, lines, (expectedResult,))
    
    def test2 (self):
        """ Seek clear """
        self.runAndAssertEquals('clearSeeks', ['<sc>'], ())
    
    def test3 (self):
        """ Seek remove (ignore remove) """
        lines = ['<s> 124 w=leaderbeans ti=02 rt=1637E t=3 i=0 r=u tp=blitz c=B rr=0-9999 a=t f=f',
                 '<sr> 124']
        self.runAndAssertEquals('removeSeek', lines, ('124',))
    
    # And so on...

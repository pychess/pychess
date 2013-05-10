import unittest
import datetime

from pychess.Utils.const import WHITE
from pychess.ic import *
from pychess.ic.FICSObjects import *
from pychess.ic.FICSConnection import Connection
from pychess.ic.VerboseTelnet import PredictionsTelnet
from pychess.ic.managers.AdjournManager import AdjournManager
from pychess.ic.managers.SeekManager import SeekManager
from pychess.ic.managers.ListAndVarManager import ListAndVarManager
from pychess.ic.managers.BoardManager import BoardManager

from Queue import Queue

class DummyConnection(Connection):
    class DummyClient(PredictionsTelnet):
        class DummyTelnet():
            def __init__(self):
                self.Q = Queue()
                self.name = "dummytelnet"
            def putline(self, line):
                self.Q.put(line)
            def write(self, text):
                pass
            def readline(self):
                return self.Q.get()
        
        def __init__(self, predictions, reply_cmd_dict):
            PredictionsTelnet.__init__(self, self.DummyTelnet(), predictions, reply_cmd_dict)
        def putline(self, line):
            self.telnet.putline(line)
    
    def __init__(self):
        Connection.__init__(self, 'host', (0,), 'tester', '123456')
        self.client = self.DummyClient(self.predictions, self.reply_cmd_dict)
        self.client.setBlockModeOn()
        self.client.setLinePrefix("fics%")
    def putline(self, line):
        self.client.putline(line)
    def handleSomeText(self):
        self.client.handleSomeText()
    def getUsername(self):
        return self.username
    
class DummyVarManager:
    def setVariable (self, name, value):
        pass
    def autoFlagNotify (self, *args):
        pass
    
class EmittingTestCase(unittest.TestCase):
    ''' Helps working with unittests on emitting objects.
        Warning: Strong connection to fics managers '''
    def runAndAssertEquals(self, signal, lines, expectedResults):
        self.args = None
        def handler(manager, *args): self.args = args
        self.manager.connect(signal, handler)
        
        for line in lines:
            self.connection.putline(line)
            self.connection.handleSomeText()
        
        self.assertNotEqual(self.args, None, "%s signal wasn't sent" % signal)
        self.assertEqual(self.args, expectedResults)

###############################################################################
# AdjournManager
###############################################################################

class AdjournManagerTests(EmittingTestCase):
    
    def setUp (self):
        self.connection = DummyConnection()
        self.connection.lvm = DummyVarManager()
        self.connection.bm = BoardManager(self.connection)
        self.connection.adm = AdjournManager(self.connection)
        self.connection.players = FICSPlayers(self.connection)
        self.connection.games = FICSGames(self.connection)
        self.manager = self.connection.adm
        
    def test1(self):
        """Testing an advanced line"""
        
        signal = 'onAdjournmentsList'
        
        lines = ['    C Opponent       On Type          Str  M    ECO Date',
            ' 1: W gbtami         N [ wr  2   2] 31-31 W18  --- Wed Dec 23, 06:58 PST 2009',
            'fics% ']
        
        gametime = datetime.datetime(2009, 12, 23, 6, 58)
        us = self.connection.players.get(FICSPlayer(self.connection.getUsername()))
        gbtami = self.connection.players.get(FICSPlayer('gbtami'))
        game = FICSAdjournedGame(us, gbtami, our_color=WHITE, length=34,
            time=gametime, rated=True, game_type=GAME_TYPES_BY_FICS_NAME['wild'],
            private=False, min=2, inc=2)
        expectedResult = [ game ]
        
        self.runAndAssertEquals(signal, lines, (expectedResult,))
    
    def test2(self):
        """Testing a double line"""
        
        signal = 'onAdjournmentsList'
        
        lines = ['    C Opponent       On Type          Str  M    ECO Date',
                 ' 1: W TheDane       N [ br  2  12]  0-0  B2   ??? Sun Nov 23,  6:14 CST 1997',
                 ' 2: W PyChess       Y [psu  2  12] 39-39 W3   C20 Sun Jan 11, 17:40 ??? 2009',
                 'fics% ']
        
        gametime1 = datetime.datetime(1997, 11, 23, 6, 14)
        gametime2 = datetime.datetime(2009, 1, 11, 17, 40)
        game1 = FICSAdjournedGame(FICSPlayer(self.connection.getUsername()),
            FICSPlayer('TheDane'), our_color=WHITE, length=3, time=gametime1,
            rated=True, game_type=GAME_TYPES['blitz'], private=False, min=2, inc=12)
        game2 = FICSAdjournedGame(FICSPlayer(self.connection.getUsername()),
            FICSPlayer('PyChess'), our_color=WHITE, length=4, time=gametime2,
            rated=False, game_type=GAME_TYPES['standard'], private=True, min=2, inc=12)

        expectedResult = [ game1, game2 ]        
        self.runAndAssertEquals(signal, lines, (expectedResult,))
    
    def test3(self):
        """ The case where player has no games in adjourned """
        
        self.runAndAssertEquals('onAdjournmentsList',
            ['%s has no adjourned games.' % self.connection.username], ([],))
    
    def test4(self):
        """ Test acquiring preview without adjournment list """
        
        signal = 'adjournedGamePreview'
        
        lines = ['BwanaSlei (1137) vs. mgatto (1336) --- Wed Nov  5, 20:56 PST 2008',
                 'Rated blitz match, initial time: 5 minutes, increment: 0 seconds.',
                 '',
                 'Move  BwanaSlei               mgatto',
                 '----  ---------------------   ---------------------',
                 '  1.  e4      (0:00.000)     c5      (0:00.000)',  
                 '  2.  Nf3     (0:00.000) ',
                 '      {White lost connection; game adjourned} *',
                 'fics% ']
        
        expectedPgn = '[Event "FICS rated blitz game"]\n[Site "FICS"]\n[White "BwanaSlei"]\n' \
                      '[Black "mgatto"]\n[TimeControl "300+0"]\n[Result "*"]\n' \
                      '[WhiteClock "0:05:00.000"]\n[BlackClock "0:05:00.000"]\n' \
                      '[WhiteElo "1137"]\n[BlackElo "1336"]\n[Year "2008"]\n' \
                      '[Month "11"]\n[Day "5"]\n[Time "20:56:00"]\n'
        expectedPgn += '1. e4 c5 2. Nf3 *\n'
        game = FICSAdjournedGame(FICSPlayer("BwanaSlei"), FICSPlayer("mgatto"),
            rated=True, game_type=GAME_TYPES["blitz"], min=5, inc=0,
            board=FICSBoard(300000, 300000, expectedPgn), reason=11)
        game.wplayer.addRating(TYPE_BLITZ, 1137)
        game.bplayer.addRating(TYPE_BLITZ, 1336)
        expectedResults = (game,)
        
        self.runAndAssertEquals(signal, lines, expectedResults)
    
    def test5(self):
        """ Test acquiring preview with adjournment list """
        
        signal = 'adjournedGamePreview'
        
        lines = ['C Opponent       On Type          Str  M    ECO Date',
                 '1: W BabyLurking     Y [ br  5   0] 29-13 W27  D37 Fri Nov  5, 04:41 PDT 2010',
                 '',
                 'mgatto (1233) vs. BabyLurking (1455) --- Fri Nov  5, 04:33 PDT 2010',
                 'Rated blitz match, initial time: 5 minutes, increment: 0 seconds.',
                 '',
                 'Move  mgatto             BabyLurking',
                 '----  ----------------   ----------------',
                 '1.  Nf3     (0:00)     d5      (0:00)',
                 '2.  d4      (0:03)     Nf6     (0:00)',
                 '3.  c4      (0:03)     e6      (0:00)',
                 '    {Game adjourned by mutual agreement} *']
        
        expectedPgn = '[Event "FICS rated blitz game"]\n[Site "FICS"]\n[White "mgatto"]\n' \
                      '[Black "BabyLurking"]\n[TimeControl "300+0"]\n[Result "*"]\n' \
                      '[WhiteClock "0:04:54.000"]\n[BlackClock "0:05:00.000"]\n' \
                      '[WhiteElo "1233"]\n[BlackElo "1455"]\n[Year "2010"]\n[Month "11"]' \
                      '\n[Day "5"]\n[Time "04:33:00"]\n1. Nf3 d5 2. d4 Nf6 3. c4 e6 *\n'
        game = FICSAdjournedGame(FICSPlayer("mgatto"), FICSPlayer("BabyLurking"),
            rated=True, game_type=GAME_TYPES["blitz"], min=5, inc=0,
            board=FICSBoard(294000, 300000, expectedPgn), reason=6)
        game.wplayer.addRating(TYPE_BLITZ, 1233)
        game.bplayer.addRating(TYPE_BLITZ, 1455)
        expectedResults = (game,)
        self.runAndAssertEquals(signal, lines, expectedResults)

###############################################################################
# SeekManager
###############################################################################

class SeekManagerTests(EmittingTestCase):
    
    def setUp (self):
        self.connection = DummyConnection()
        # The real one stucks
        #self.connection.lvm = ListAndVarManager(self.connection)
        self.connection.lvm = DummyVarManager()
        self.manager = SeekManager(self.connection)
    
    def test1 (self):
        """ Seek add """
        
        signal = 'addSeek'
        
        lines = ['<s> 10 w=warbly ti=00 rt=1291  t=3 i=0 r=r tp=blitz c=? rr=1200-1400 a=t f=t']
        expectedResult = {'gameno':'10', 'gametype': GAME_TYPES["blitz"],
            'rmin':1200, 'rmax':1400, 'cp':False, 'rt':'1291', 'manual':False,
            'title': '', 'w':'warbly', 'r':'r', 't':'3', 'i':'0'}
        self.runAndAssertEquals(signal, lines, (expectedResult,))
        
        lines = ['<s> 124 w=leaderbeans ti=02 rt=1637E t=3 i=0 r=u tp=blitz c=B rr=0-9999 a=t f=f']
        expectedResult = {'gameno':'124', 'gametype': GAME_TYPES["blitz"],
            'rmin':0, 'rmax':9999, 'cp':True, 'rt':'1637', 'manual':False,
            'title': '(C)', 'w':'leaderbeans', 'r':'u', 't':'3', 'i':'0'}
        self.runAndAssertEquals(signal, lines, (expectedResult,))

        lines = ['<s> 14 w=microknight ti=00 rt=1294  t=15 i=0 r=u tp=standard c=? rr=1100-1450 a=f f=f']
        expectedResult = {'gameno':'14', 'gametype': GAME_TYPES["standard"],
            'rmin':1100, 'rmax':1450, 'cp':False, 'rt':'1294', 'manual':True,
            'title': '', 'w':'microknight', 'r':'u', 't':'15', 'i':'0'}
        self.runAndAssertEquals(signal, lines, (expectedResult,))
    
    def test2 (self):
        """ Seek clear """
        self.runAndAssertEquals('clearSeeks', ['<sc>'], ())
    
    def test3 (self):
        """ Seek remove (ignore remove) """
        lines = ['<s> 124 w=leaderbeans ti=02 rt=1637E t=3 i=0 r=u tp=blitz c=B rr=0-9999 a=t f=f',
                 '<sr> 124']
        self.runAndAssertEquals('removeSeek', lines, ('124',))
    
    def test4 (self):
        # This test case should be implemented when the ficsmanager.py unit testing
        # is able to chain managers like the real fics code does. This is because
        # this test case tests verifies that this line is caught in BoardManager.py
        # rather than being accidentally caught by the on_player_list() regex in
        # GameManager.py (or elsewhere).
        #
        #lines = ['Game 342: Game clock paused.']
        pass
    
    # And so on...

if __name__ == '__main__':
    unittest.main()

import unittest
import datetime
import random

from pychess.compat import Queue, Empty
from pychess.Utils.const import WHITE
from pychess.Utils.TimeModel import TimeModel
from pychess.ic import *
from pychess.ic.FICSObjects import *
from pychess.ic.ICGameModel import ICGameModel
from pychess.ic.FICSConnection import Connection
from pychess.ic.VerboseTelnet import PredictionsTelnet, ConsoleHandler, TelnetLine
from pychess.ic.managers.AdjournManager import AdjournManager
from pychess.ic.managers.SeekManager import SeekManager
from pychess.ic.managers.ListAndVarManager import ListAndVarManager
from pychess.ic.managers.BoardManager import BoardManager
from pychess.ic.managers.OfferManager import OfferManager
from pychess.ic.managers.HelperManager import HelperManager
from pychess.ic.managers.ErrorManager import ErrorManager
from pychess.ic.managers.FingerManager import FingerManager
from pychess.ic.managers.NewsManager import NewsManager
from pychess.ic.managers.ChatManager import ChatManager
from pychess.ic.managers.ConsoleManager import ConsoleManager
from pychess.ic.managers.AutoLogOutManager import AutoLogOutManager

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
                return self.Q.get_nowait()
        
        def __init__(self, predictions, reply_cmd_dict):
            PredictionsTelnet.__init__(self, self.DummyTelnet(), predictions, reply_cmd_dict)
            self.commands = []
        def putline(self, line):
            self.telnet.putline(line)
        def run_command(self, command):
            self.commands.append(command)
    
    def __init__(self):
        Connection.__init__(self, 'host', (0,), 'tester', '123456')
        class fake_set (list):
            def __init__(self, *args):
                list.__init__(self, args)
            def add(self, x):
                self.append(x)
        self.predictions = fake_set() # make predictions able to be reordered
        self.client = self.DummyClient(self.predictions, self.reply_cmd_dict)
        self.client.lines.block_mode = True
        self.client.lines.line_prefix = "fics%"
        self.examined_game = None
        
    def getUsername(self):
        return self.username
    def putline(self, line):
        self.client.putline(line)
    def process_line(self):
        self.client.parse()
    def process_lines(self, lines):
        for line in lines:
            self.putline(line)
        while True:
            try:
                self.process_line()
            except Empty:
                break
    
class DummyVarManager:
    def setVariable (self, name, value):
        pass
    def autoFlagNotify (self, *args):
        pass
    
class EmittingTestCase(unittest.TestCase):
    ''' Helps working with unittests on emitting objects.
        Warning: Strong connection to fics managers '''
    def setUp (self):
        self.connection = DummyConnection()
        self.connection.players = FICSPlayers(self.connection)
        self.connection.games = FICSGames(self.connection)
        self.connection.seeks = FICSSeeks(self.connection)
        self.connection.challenges = FICSChallenges(self.connection)
        # The real one freezes
        #self.connection.lvm = ListAndVarManager(self.connection)
        self.connection.lvm = DummyVarManager()
        self.connection.hm = HelperManager(self.connection, self.connection)
        self.connection.em = ErrorManager(self.connection)
        self.connection.glm = SeekManager(self.connection)
        self.connection.bm = BoardManager(self.connection)
        self.connection.fm = FingerManager(self.connection)
        self.connection.nm = NewsManager(self.connection)
        self.connection.om = OfferManager(self.connection)
        self.connection.cm = ChatManager(self.connection)
        self.connection.alm = AutoLogOutManager(self.connection)
        self.connection.adm = AdjournManager(self.connection)
        self.connection.com = ConsoleManager(self.connection)
        self.connection.bm.start()
        self.connection.players.start()
        self.connection.games.start()
        self.connection.seeks.start()
        self.connection.challenges.start()
        
    def runAndAssertEquals(self, signal, lines, expectedResults):
        self.args = None
        def handler(manager, *args):
            self.args = args
            #print(signal, args[0])
            if signal == "obsGameCreated":
                ficsgame = args[0]
                self.connection.bm.onGameModelStarted(ficsgame.gameno)
        self.manager.connect(signal, handler)

        random.shuffle(self.connection.client.predictions)
        self.connection.process_lines(lines)
        self.assertNotEqual(self.args, None, "%s signal wasn't sent" % signal)
        self.assertEqual(self.args, expectedResults)
        
    def runAndAssertEqualsNotify(self, obj, prop, lines, expectedResults):
        self.args = None
        self.prop_value = None
        def handler(obj, *args):
            self.args = args
            self.prop_value = getattr(obj, prop)
        obj.connect('notify::'+prop, handler)
        random.shuffle(self.connection.client.predictions)
        self.connection.process_lines(lines)
        self.assertNotEqual(self.args, None,
            "no \'%s\' property change notification for %s" % (prop, repr(obj)))
        self.assertEqual(self.prop_value, expectedResults)

    def runAndAssertEqualPropValue(self, signal, lines, prop, expectedResult):
        self.prop_value = None
        def handler(manager, arg):
            self.prop_value = getattr(arg, prop)
        self.manager.connect(signal, handler)
        random.shuffle(self.connection.client.predictions)
        self.connection.process_lines(lines)
        self.assertNotEqual(self.prop_value, None, "%s signal wasn't sent" % signal)
        self.assertEqual(self.prop_value, expectedResult)
        
###############################################################################
# AdjournManager
###############################################################################

class AdjournManagerTests(EmittingTestCase):
    
    def setUp (self):
        EmittingTestCase.setUp(self)
        self.manager = self.connection.adm
        
    def test1(self):
        """Testing an advanced line"""
        
        signal = 'onAdjournmentsList'
        
        lines = ['Stored games for tester:',
                 '    C Opponent       On Type          Str  M    ECO Date',
                 ' 1: W gbtami         N [ wr  2   2] 31-31 W18  --- Wed Dec 23, 06:58 PST 2009',
                 'fics% ']
        
        gametime = datetime.datetime(2009, 12, 23, 6, 58)
        us = self.connection.players.get(FICSPlayer(self.connection.getUsername()))
        gbtami = self.connection.players.get(FICSPlayer('gbtami'))
        game = FICSAdjournedGame(us, gbtami, our_color=WHITE, length=34,
            time=gametime, rated=True, game_type=GAME_TYPES_BY_FICS_NAME['wild'],
            private=False, minutes=2, inc=2)
        expectedResult = [ game ]
        
        self.runAndAssertEquals(signal, lines, (expectedResult,))
    
    def test2(self):
        """Testing a double line"""
        
        signal = 'onAdjournmentsList'
        
        lines = ['Stored games for tester:',
                 '    C Opponent       On Type          Str  M    ECO Date',
                 ' 1: W TheDane       N [ br  2  12]  0-0  B2   ??? Sun Nov 23,  6:14 CST 1997',
                 ' 2: W PyChess       Y [psu  2  12] 39-39 W3   C20 Sun Jan 11, 17:40 ??? 2009',
                 'fics% ']
        
        gametime1 = datetime.datetime(1997, 11, 23, 6, 14)
        gametime2 = datetime.datetime(2009, 1, 11, 17, 40)
        game1 = FICSAdjournedGame(FICSPlayer(self.connection.getUsername()),
            FICSPlayer('TheDane'), our_color=WHITE, length=3, time=gametime1,
            rated=True, game_type=GAME_TYPES['blitz'], private=False, minutes=2, inc=12)
        game2 = FICSAdjournedGame(FICSPlayer(self.connection.getUsername()),
            FICSPlayer('PyChess'), our_color=WHITE, length=4, time=gametime2,
            rated=False, game_type=GAME_TYPES['standard'], private=True, minutes=2, inc=12)

        expectedResult = [ game1, game2 ]        
        self.runAndAssertEquals(signal, lines, (expectedResult,))
    
    def test3(self):
        """ The case where player has no games in adjourned """
        
        self.runAndAssertEquals('onAdjournmentsList',
            ['%s has no adjourned games.' % self.connection.username], ([],))
    

###############################################################################
# SeekManager
###############################################################################

class SeekManagerTests(EmittingTestCase):
    
    def setUp (self):
        EmittingTestCase.setUp(self)
        self.manager = self.connection.glm
    
    def test1 (self):
        lines = ['<s> 10 w=warbly ti=00 rt=1291  t=3 i=0 r=r tp=blitz c=? rr=1200-1400 a=t f=t']
        player = FICSPlayer('warbly')
        player.ratings[TYPE_BLITZ].elo = 1291
        expectedResult = FICSSeek(10, player, 3, 0, True, None,
            GAME_TYPES["blitz"], rmin=1200, rmax=1400, formula=True)
        self.runAndAssertEquals('addSeek', lines, (expectedResult,))
        
    def test2 (self):
        lines = ['<s> 124 w=leaderbeans ti=02 rt=1637E t=3 i=0 r=u tp=blitz c=B rr=0-9999 a=t f=f']
        player = FICSPlayer('leaderbeans')
        player.ratings[TYPE_BLITZ].elo = 1637
        player.ratings[TYPE_BLITZ].deviation = DEVIATION_ESTIMATED
        player.titles |= set((TYPE_COMPUTER,))
        expectedResult = FICSSeek(124, player, 3, 0, False, 'black',
                                  GAME_TYPES["blitz"])
        self.runAndAssertEquals('addSeek', lines, (expectedResult,))

    def test3 (self):
        lines = ['<s> 14 w=microknight ti=00 rt=1294  t=15 i=0 r=u tp=standard c=? rr=1100-1450 a=f f=f']
        player = FICSPlayer('microknight')
        player.ratings[TYPE_BLITZ].elo = 1294
        expectedResult = FICSSeek(14, player, 15, 0, False, None,
            GAME_TYPES["standard"], rmin=1100, rmax=1450, automatic=False)
        self.runAndAssertEquals('addSeek', lines, (expectedResult,))
    
    def test4 (self):
        """ Seek clear """
        self.runAndAssertEquals('clearSeeks', ['<sc>'], ())
    
    def test5 (self):
        """ Seek remove """
        lines = ['<s> 124 w=leaderbeans ti=02 rt=1637E t=3 i=0 r=u tp=blitz c=B rr=0-9999 a=t f=f',
                 '<sr> 124', '']
        self.runAndAssertEquals('removeSeek', lines, (124,))
    
    def test6 (self):
        """ Seek add resulting from a seek command reply """
        lines = [BLOCK_START + '54' + BLOCK_SEPARATOR + '155' + BLOCK_SEPARATOR,
                 '<sn> 121 w=mgatto ti=00 rt=1677  t=6 i=1 r=r tp=wild/4 c=? rr=0-9999 a=f f=f',
                 'fics% Your seek has been posted with index 121.',
                 '(9 player(s) saw the seek.)',
                 BLOCK_END]
        player = FICSPlayer('mgatto')
        player.ratings[TYPE_BLITZ].elo = 1677
        expectedResult = FICSSeek(121, player, 6, 1, True, None,
            GAME_TYPES["wild/4"], automatic=False)
        self.runAndAssertEquals('addSeek', lines, (expectedResult,))
    
    def test7 (self):
        """ Confirm that seeks remove resulting from an unseek command reply
            is caught by our_seeks_removed rather than on_seek_remove
        """
        lines = [BLOCK_START + '54' + BLOCK_SEPARATOR + '156' + BLOCK_SEPARATOR,
                 "<sr> 8 17 30",
                 "Your seeks have been removed.",
                 BLOCK_END]
        self.runAndAssertEquals('our_seeks_removed', lines, ())

    def test8 (self):
        lines = [BLOCK_START + '62' + BLOCK_SEPARATOR + '155' + BLOCK_SEPARATOR +
                 "Updating seek ad 105 to automatic.",
                 "",
                 "<sr> 105",
                 "",
                 "<sn> 105 w=mgatto ti=00 rt=1651  t=3 i=0 r=r tp=wild/4 c=? rr=1375-1925 a=t f=f",
                 "Your seek has been posted with index 105.",
                 "(2 player(s) saw the seek.)",
                 BLOCK_END]
        self.runAndAssertEquals('seek_updated', lines, ('to automatic',))
    
    def test9 (self):
        lines = [BLOCK_START + '62' + BLOCK_SEPARATOR + '155' + BLOCK_SEPARATOR +
                 "Updating seek ad 12 to manual.",
                 "Updating seek ad 12; rating range now 0-9999.",
                 "",
                 "<sr> 12",
                 "",
                 "<sn> 12 w=mgatto ti=00 rt=1640  t=3 i=0 r=r tp=wild/4 c=? rr=0-9999 a=f f=f",
                 "Your seek has been posted with index 12.",
                 "(11 player(s) saw the seek.)",
                 BLOCK_END]
        self.runAndAssertEquals('seek_updated', lines, ('to manual; rating range now 0-9999',))

    def test10 (self):
        """ Seek add resulting from a seek matches command reply """
        lines = [BLOCK_START + '66' + BLOCK_SEPARATOR + '155' + BLOCK_SEPARATOR,
                 "Your seek matches one already posted by Bezo.",
                 "Issuing match request since the seek was set to manual.",
                 "Issuing: gbtami (1671) Bezo (1569) rated lightning 1 0.",
                 "Your lightning rating will change:  Win: +6,  Draw: -2,  Loss: -10",
                 "Your new RD will be 22.9",
                 "",
                 "<pt> 32 w=Bezo t=match p=gbtami (1671) Bezo (1569) rated lightning 1 0",
                 "fics%",
                 "Your seek matches one already posted by BugMashine.",
                 "Issuing match request since the seek was set to manual.",
                 "Issuing: gbtami (1671) BugMashine (1692) rated lightning 1 0.",
                 "Your lightning rating will change:  Win: +8,  Draw: +0,  Loss: -8",
                 "Your new RD will be 22.9",
                 "",
                 "<pt> 34 w=BugMashine t=match p=gbtami (1671) BugMashine (1692) rated lightning 1 0",
                 "fics%",
                 "",
                 "<sn> 46 w=gbtami ti=00 rt=1671  t=1 i=0 r=r tp=lightning c=? rr=1500-1700 a=t f=f",
                 "fics% Your seek has been posted with index 46.",
                 "(2 player(s) saw the seek.)",
                 BLOCK_END]
        player = FICSPlayer('gbtami')
        player.ratings[TYPE_BLITZ].elo = 1671
        expectedResult = FICSSeek(46, player, 1, 0, True, None,
            GAME_TYPES["lightning"], automatic=False)
        self.runAndAssertEquals('addSeek', lines, (expectedResult,))

class BoardManagerTests(EmittingTestCase):
    
    def setUp (self):
        EmittingTestCase.setUp(self)
        self.manager = self.connection.bm

        self.deleted_offers = set()
        def pr_handler(manager, offer): self.deleted_offers.add(offer)
        self.connection.om.connect('onChallengeRemove', pr_handler)

        self.deleted_seeks = set()
        def sr_handler(manager, seek): self.deleted_seeks.add(seek)
        self.connection.glm.connect('removeSeek', sr_handler)
    
    def match_offer(self, offer):
        return "<pf> %s w=GuestABCD t=match p=GuestABCD (----) [black] GuestEFGH (----) unrated untimed" % offer

    def test1 (self):
        lines = [BLOCK_START + '110' + BLOCK_SEPARATOR + '155' + BLOCK_SEPARATOR,
                 "Your seek matches one already posted by Thegermain.",
                 "",
                 "<sr> 111 25",
                 "fics%" ,
                 "<sr> 153",
                 "fics%" ,
                 "Creating: mgatto (1327) Thegermain (1645) unrated blitz 4 0",
                 "{Game 55 (mgatto vs. Thegermain) Creating unrated blitz match.}",
                 "",
                 "<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 55 mgatto Thegermain 1 4 0 39 39 240000 240000 1 none (0:00.000) none 0 0 0",
                 BLOCK_END]
        me = self.connection.players.get(FICSPlayer('mgatto'))
        me.ratings[TYPE_BLITZ].elo = 1327
        opponent = self.connection.players.get(FICSPlayer('Thegermain'))
        opponent.ratings[TYPE_BLITZ].elo = 1645
        game = FICSGame(me, opponent, gameno=55, rated=False,
            game_type=GAME_TYPES['blitz'], private=False, minutes=4, inc=0,
            board=FICSBoard(240000, 240000, fen=FEN_START))
        me.game = game
        opponent.game = game
        self.runAndAssertEquals("playGameCreated", lines, (game,))
        self.assertEqual(self.deleted_seeks, set((111, 25, 153)))
    
    def test2 (self):
        lines = [BLOCK_START + '111' + BLOCK_SEPARATOR + '155' + BLOCK_SEPARATOR,
                 "Your seek matches one already posted by GuestRLJC.",
                 "",
                 "<sr> 135",
                 "fics%" ,
                 "Creating: mgatto (1305) GuestRLJC (++++) unrated blitz 5 0",
                 "{Game 442 (mgatto vs. GuestRLJC) Creating unrated blitz match.}",
                 "",
                 "<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 442 mgatto GuestRLJC 1 5 0 39 39 300000 300000 1 none (0:00.000) none 0 0 0",
                 BLOCK_END]
        me = self.connection.players.get(FICSPlayer('mgatto'))
        me.ratings[TYPE_BLITZ].elo = 1305
        opponent = self.connection.players.get(FICSPlayer('GuestRLJC'))
        game = FICSGame(me, opponent, gameno=442, rated=False,
            game_type=GAME_TYPES['blitz'], private=False, minutes=5, inc=0,
            board=FICSBoard(300000, 300000, fen=FEN_START))
        me.game = game
        opponent.game = game
        self.runAndAssertEquals("playGameCreated", lines, (game,))
        self.assertEqual(self.deleted_seeks, set((135,)))
    
    def test3 (self):
        lines = [self.match_offer(11),
                 BLOCK_START + '172' + BLOCK_SEPARATOR + '155' + BLOCK_SEPARATOR,
                 "Your seek matches one already posted by suugakusya.",
                 "",
                 "<sr> 89",
                 "fics%" ,
                 "<sr> 90",
                 "fics% Challenge to archmagician withdrawn.",
                 "",
                 "<pr> 11",
                 "fics%",
                 "Creating: gbtami (1529) suugakusya (1425) rated blitz 5 5",
                 "{Game 101 (gbtami vs. suugakusya) Creating rated blitz match.}",
                 "",
                 "<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 101 gbtami suugakusya 1 5 5 39 39 300000 300000 1 none (0:00.000) none 0 0 0",
                 "",
                 "Game 101: A disconnection will be considered a forfeit.",
                 BLOCK_END]
        me = self.connection.players.get(FICSPlayer('gbtami'))
        me.ratings[TYPE_BLITZ].elo = 1529
        opponent = self.connection.players.get(FICSPlayer('suugakusya'))
        opponent.ratings[TYPE_BLITZ].elo = 1425
        game = FICSGame(me, opponent, gameno=101, rated=True,
            game_type=GAME_TYPES['blitz'], private=False, minutes=5, inc=5,
            board=FICSBoard(300000, 300000, fen=FEN_START))
        me.game = game
        opponent.game = game
        self.runAndAssertEquals("playGameCreated", lines, (game,))
        self.assertEqual(self.deleted_seeks, set((89, 90)))
        self.assertEqual(self.deleted_offers, set((11,)))
    
    def test4 (self):
        lines = [self.match_offer(11),
                 BLOCK_START + '172' + BLOCK_SEPARATOR + '155' + BLOCK_SEPARATOR,
                 "Your seek matches one already posted by suugakusya.",
                 "",
                 "<sr> 89",
                 "fics% Challenge to archmagician withdrawn.",
                 "",
                 "<pr> 11",
                 "fics%",
                 "Creating: gbtami (1529) suugakusya (1425) rated blitz 5 5",
                 "{Game 101 (gbtami vs. suugakusya) Creating rated blitz match.}",
                 "",
                 "<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 101 gbtami suugakusya 1 5 5 39 39 300000 300000 1 none (0:00.000) none 0 0 0",
                 "",
                 "Game 101: A disconnection will be considered a forfeit.",
                 BLOCK_END]
        me = self.connection.players.get(FICSPlayer('gbtami'))
        me.ratings[TYPE_BLITZ].elo = 1529
        opponent = self.connection.players.get(FICSPlayer('suugakusya'))
        opponent.ratings[TYPE_BLITZ].elo = 1425
        game = FICSGame(me, opponent, gameno=101, rated=True,
            game_type=GAME_TYPES['blitz'], private=False, minutes=5, inc=5,
            board=FICSBoard(300000, 300000, fen=FEN_START))
        me.game = game
        opponent.game = game
        self.runAndAssertEquals("playGameCreated", lines, (game,))
        self.assertEqual(self.deleted_seeks, set((89,)))
        self.assertEqual(self.deleted_offers, set((11,)))
    
    def test5 (self):
        lines = [self.match_offer(39),
                 BLOCK_START + '213' + BLOCK_SEPARATOR + '155' + BLOCK_SEPARATOR,
                 "Your seek matches one already posted by chemo.",
                 "",
                 "<sr> 6",
                 "fics%",
                 "Challenge from yms removed.",
                 "",
                 "<pr> 39",
                 "fics%",
                 "Creating: chemo (1749) mgatto (1547) rated lightning 1 0",
                 "{Game 512 (chemo vs. mgatto) Creating rated lightning match.}",
                 "",
                 "<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 512 chemo mgatto -1 1 0 39 39 60000 60000 1 none (0:00.000) none 1 0 0",
                 BLOCK_END]
        me = self.connection.players.get(FICSPlayer('mgatto'))
        me.ratings[TYPE_BLITZ].elo = 1547
        opponent = self.connection.players.get(FICSPlayer('chemo'))
        opponent.ratings[TYPE_BLITZ].elo = 1749
        game = FICSGame(opponent, me, gameno=512, rated=True,
            game_type=GAME_TYPES['blitz'], private=False, minutes=1, inc=0,
            board=FICSBoard(60000, 60000, fen=FEN_START))
        me.game = game
        opponent.game = game
        self.runAndAssertEquals("playGameCreated", lines, (game,))
        self.assertEqual(self.deleted_seeks, set((6,)))
        self.assertEqual(self.deleted_offers, set((39,)))
    
    def test6 (self):
        lines = [self.match_offer(53),
                 BLOCK_START + '172' + BLOCK_SEPARATOR + '155' + BLOCK_SEPARATOR,
                 "Your seek matches one already posted by fabk.",
                 "",
                 "<sr> 93 71",
                 "fics%",
                 "<pr> 53",
                 "fics%",
                 "Creating: fabk (1155) mgatto (1470) rated lightning 1 0",
                 "{Game 465 (fabk vs. mgatto) Creating rated lightning match.}",
                 "",
                 "<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 465 fabk mgatto -1 1 0 39 39 60000 60000 1 none (0:00.000) none 1 0 0",
                 "",
                 "Game 465: A disconnection will be considered a forfeit.",
                 BLOCK_END]
        me = self.connection.players.get(FICSPlayer('mgatto'))
        me.ratings[TYPE_BLITZ].elo = 1470
        opponent = self.connection.players.get(FICSPlayer('fabk'))
        opponent.ratings[TYPE_BLITZ].elo = 1155
        game = FICSGame(opponent, me, gameno=465, rated=True,
            game_type=GAME_TYPES['lightning'], private=False, minutes=1, inc=0,
            board=FICSBoard(60000, 60000, fen=FEN_START))
        me.game = game
        opponent.game = game
        self.runAndAssertEquals("playGameCreated", lines, (game,))
        self.assertEqual(self.deleted_seeks, set((93, 71)))
        self.assertEqual(self.deleted_offers, set((53,)))
    
    def test7 (self):
        lines = [BLOCK_START + '111' + BLOCK_SEPARATOR + '155' + BLOCK_SEPARATOR,
                 "Your seek qualifies for antiseptic's getgame.",
                 "",
                 "<sr> 145",
                 "fics%" ,
                 "Creating: antiseptic (1917) mgatto (1683) rated wild/4 5 2",
                 "{Game 54 (antiseptic vs. mgatto) Creating rated wild/4 match.}",
                 "",
                 "<12> knnrrrqn pppppppp -------- -------- -------- -------- PPPPPPPP NRNKNQRR W -1 0 0 0 0 0 54 antiseptic mgatto -1 5 2 41 41 300000 300000 1 none (0:00.000) none 1 0 0",
                 BLOCK_END]
        me = self.connection.players.get(FICSPlayer('mgatto'))
        me.ratings[TYPE_BLITZ].elo = 1305
        opponent = self.connection.players.get(FICSPlayer('antiseptic'))
        game = FICSGame(opponent, me, gameno=54, rated=True,
            game_type=GAME_TYPES['wild/4'], private=False, minutes=5, inc=2,
            board=FICSBoard(300000, 300000, fen="knnrrrqn pppppppp -------- -------- -------- -------- PPPPPPPP NRNKNQRR W -1 0 0 0 0 0"))
        me.game = game
        opponent.game = game
        self.runAndAssertEquals("playGameCreated", lines, (game,))
        self.assertEqual(self.deleted_seeks, set((145,)))

    def test8 (self):
        lines = [BLOCK_START + '111' + BLOCK_SEPARATOR + '155' + BLOCK_SEPARATOR,
                 "Your seek qualifies for opmentor's getgame.",
                 "",
                 "<sr> 179",
                 "fics%" ,
                 "<sr> 3",
                 "fics%" ,
                 "Creating: opmentor (++++) mgatto (1343) unrated lightning 2 1",
                 "{Game 107 (opmentor vs. mgatto) Creating unrated lightning match.}",
                 "",
                 "<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 107 opmentor mgatto -1 2 1 39 39 120000 120000 1 none (0:00.000) none 1 0 0",
                 BLOCK_END]
        me = self.connection.players.get(FICSPlayer('mgatto'))
        opponent = self.connection.players.get(FICSPlayer('opmentor'))
        game = FICSGame(opponent, me, gameno=107, rated=False,
            game_type=GAME_TYPES['lightning'], private=False, minutes=2, inc=1,
            board=FICSBoard(120000, 120000,  fen=FEN_START))
        me.game = game
        opponent.game = game
        self.runAndAssertEquals("playGameCreated", lines, (game,))
        self.assertEqual(self.deleted_seeks, set((179, 3)))

    def test9 (self):
        lines = [self.match_offer(6),
                 BLOCK_START + '538' + BLOCK_SEPARATOR + '155' + BLOCK_SEPARATOR,
                 "Your seek qualifies for opmentor's getgame.",
                 "",
                 "<sr> 33",
                 "fics% Challenge to georgespock withdrawn." ,
                 "",
                 "<pr> 6",
                 "fics%",
                 "Creating: opmentor (++++) mgatto (1576) unrated lightning 1 0",
                 "{Game 72 (opmentor vs. mgatto) Creating unrated lightning match.}",
                 "",
                 "<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 72 opmentor mgatto -1 1 0 39 39 60000 60000 1 none (0:00.000) none 1 0 0",
                 "",
                 "Game 72: A disconnection will be considered a forfeit.",
                 BLOCK_END]
        me = self.connection.players.get(FICSPlayer('mgatto'))
        opponent = self.connection.players.get(FICSPlayer('opmentor'))
        game = FICSGame(opponent, me, gameno=72, rated=False,
            game_type=GAME_TYPES['lightning'], private=False, minutes=1, inc=0,
            board=FICSBoard(60000, 60000,  fen=FEN_START))
        me.game = game
        opponent.game = game
        self.runAndAssertEquals("playGameCreated", lines, (game,))
        self.assertEqual(self.deleted_offers, set((6,)))
        self.assertEqual(self.deleted_seeks, set((33,)))

    def test10 (self):
        lines = [self.match_offer(14),
                 self.match_offer(9),
                 BLOCK_START + '110' + BLOCK_SEPARATOR + '155' + BLOCK_SEPARATOR,
                 "Your seek matches one already posted by Strix.",
                 "",
                 "<sr> 68 105",
                 "fics%" ,
                 "<sr> 89",
                 "fics% Challenge to yunger withdrawn.",
                 "",
                 "<pr> 14",
                 "fics% Challenge to joranday withdrawn.",
                 "",
                 "<pr> 9",
                 "fics%",
                 "Creating: gbtami (1626) Strix (1581) rated blitz 3 0",
                 "{Game 333 (gbtami vs. Strix) Creating rated blitz match.}",
                 "",
                 "<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 333 gbtami Strix 1 3 0 39 39 180000 180000 1 none (0:00.000) none 0 0 0",
                 "",
                 "Game 333: A disconnection will be considered a forfeit.",
                 BLOCK_END]
        me = self.connection.players.get(FICSPlayer('gbtami'))
        me.ratings[TYPE_BLITZ].elo = 1626
        opponent = self.connection.players.get(FICSPlayer('Strix'))
        opponent.ratings[TYPE_BLITZ].elo = 1581
        game = FICSGame(me, opponent, gameno=333, rated=True,
            game_type=GAME_TYPES['blitz'], private=False, minutes=3, inc=0,
            board=FICSBoard(180000, 180000, fen=FEN_START))
        me.game = game
        opponent.game = game
        self.runAndAssertEquals("playGameCreated", lines, (game,))
        self.assertEqual(self.deleted_offers, set((14, 9)))
        self.assertEqual(self.deleted_seeks, set((68, 105, 89)))

    def test11 (self):
        lines = [self.match_offer(12),
                 BLOCK_START + '279' + BLOCK_SEPARATOR + '155' + BLOCK_SEPARATOR,
                 "Your seek matches one already posted by coopnomaks.",
                 "",
                 "<sr> 125 127",
                 "fics%" ,
                 "<sr> 109",
                 "fics%",
                 "Challenge from Deji withdrawn.",
                 "",
                 "<pr> 12",
                 "fics%",
                 "Creating: coopnomaks (1570) gbtami (1609) rated blitz 3 0",
                 "{Game 501 (coopnomaks vs. gbtami) Creating rated blitz match.}",
                 "",
                 "<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 501 coopnomaks gbtami -1 3 0 39 39 180000 180000 1 none (0:00.000) none 0 0 0",
                 "",
                 "Game 501: A disconnection will be considered a forfeit.",
                 BLOCK_END]
        me = self.connection.players.get(FICSPlayer('gbtami'))
        me.ratings[TYPE_BLITZ].elo = 1609
        opponent = self.connection.players.get(FICSPlayer('coopnomaks'))
        opponent.ratings[TYPE_BLITZ].elo = 1570
        game = FICSGame(opponent, me, gameno=501, rated=True,
            game_type=GAME_TYPES['blitz'], private=False, minutes=3, inc=0,
            board=FICSBoard(180000, 180000, fen=FEN_START))
        me.game = game
        opponent.game = game
        self.runAndAssertEquals("playGameCreated", lines, (game,))
        self.assertEqual(self.deleted_offers, set((12,)))
        self.assertEqual(self.deleted_seeks, set((125, 127, 109)))

    def test12 (self):
        lines = [self.match_offer(4),
                 BLOCK_START + '321' + BLOCK_SEPARATOR + '73' + BLOCK_SEPARATOR,
                 "Your challenge intercepts pianazo's challenge.",
                 "",
                 "<pr> 4",
                 "fics%" ,
                 "Creating: gbtami (1475) pianazo (1520) rated blitz 3 0",
                 "{Game 422 (gbtami vs. pianazo) Creating rated blitz match.}",
                 "",
                 "<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 422 gbtami pianazo 1 3 0 39 39 180000 180000 1 none (0:00.000) none 0 0 0",
                 "",
                 "Game 422: A disconnection will be considered a forfeit.",
                 BLOCK_END]
        me = self.connection.players.get(FICSPlayer('gbtami'))
        me.ratings[TYPE_BLITZ].elo = 1475
        opponent = self.connection.players.get(FICSPlayer('pianazo'))
        opponent.ratings[TYPE_BLITZ].elo = 1520
        game = FICSGame(me, opponent, gameno=422, rated=True,
            game_type=GAME_TYPES['blitz'], private=False, minutes=3, inc=0,
            board=FICSBoard(180000, 180000, fen=FEN_START))
        me.game = game
        opponent.game = game
        self.runAndAssertEquals("playGameCreated", lines, (game,))
        self.assertEqual(self.deleted_offers, set((4,)))

    def test13 (self):
        lines = [self.match_offer(25),
                 BLOCK_START + '321' + BLOCK_SEPARATOR + '73' + BLOCK_SEPARATOR,
                 "Your challenge intercepts clisus's challenge.",
                 "",
                 "<sr> 117",
                 "fics%" ,
                 "<pr> 25",
                 "fics%" ,
                 "Creating: clisus (1470) mgatto (1542) rated lightning 1 0",
                 "{Game 225 (clisus vs. mgatto) Creating rated lightning match.}",
                 "",
                 "<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 225 clisus mgatto -1 1 0 39 39 60000 60000 1 none (0:00.000) none 1 0 0",
                 BLOCK_END]
        me = self.connection.players.get(FICSPlayer('mgatto'))
        me.ratings[TYPE_BLITZ].elo = 1542
        opponent = self.connection.players.get(FICSPlayer('clisus'))
        opponent.ratings[TYPE_BLITZ].elo = 1470
        game = FICSGame(opponent, me, gameno=225, rated=True,
            game_type=GAME_TYPES['lightning'], private=False, minutes=1, inc=0,
            board=FICSBoard(60000, 60000, fen=FEN_START))
        me.game = game
        opponent.game = game
        self.runAndAssertEquals("playGameCreated", lines, (game,))
        self.assertEqual(self.deleted_offers, set((25,)))
        self.assertEqual(self.deleted_seeks, set((117,)))

    def test14 (self):
        """ Make sure observe-game-created messages are caught """
        lines = ["{Game 12 (electricbenj vs. antonymelvin) Creating rated wild/fr match.}",
                 BLOCK_START + '34' + BLOCK_SEPARATOR + '80' + BLOCK_SEPARATOR,
                 "You are now observing game 12.",
                 "Game 12: electricbenj (1535) antonymelvin (1507) rated wild/fr 7 8",
                 "",
                 "<12> -------r pbp--p-- -pn-k--p -Q------ -----qP- -------- PPP--n-- -K-RR--- B -1 0 0 0 0 1 12 electricbenj antonymelvin 0 7 8 23 28 346573 428761 22 R/h1-e1 (0:11.807) Rhe1+ 0 1 0",
                 BLOCK_END]
        self.connection.process_lines(lines)
        self.assertEqual(self.connection.client.commands[-1], "moves 12")

    def test15(self):
        """ Test acquiring preview without adjournment list """
        
        signal = 'archiveGamePreview'
        
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
            rated=True, game_type=GAME_TYPES["blitz"], minutes=5, inc=0,
            board=FICSBoard(300000, 300000, expectedPgn), reason=11)
        game.wplayer.ratings[TYPE_BLITZ].elo = 1137
        game.bplayer.ratings[TYPE_BLITZ].elo = 1336
        expectedResults = (game,)
        
        self.runAndAssertEquals(signal, lines, expectedResults)
    
    def test16(self):
        """ Test acquiring preview with adjournment list """
        
        signal = 'archiveGamePreview'
        
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
            rated=True, game_type=GAME_TYPES["blitz"], minutes=5, inc=0,
            board=FICSBoard(294000, 300000, expectedPgn), reason=6)
        game.wplayer.ratings[TYPE_BLITZ].elo = 1233
        game.bplayer.ratings[TYPE_BLITZ].elo = 1455
        expectedResults = (game,)
        self.runAndAssertEquals(signal, lines, expectedResults)


    def test17(self):
        """ Test observing game """
        
        lines = ["{Game 463 (schachbjm vs. Maras) Creating rated standard match.}",
                 BLOCK_START + '34' + BLOCK_SEPARATOR + '80' + BLOCK_SEPARATOR,
                 'You are now observing game 463.',
                'Game 463: schachbjm (2243) Maras (2158E) rated standard 45 45',
                '',
                '<12> -r------ --k----- ----p--- n-ppPb-p -----P-P -PP-K-P- PR------ --R----- W -1 0 0 0 0 11 463 schachbjm Maras 0 45 45 17 15 557871 274070 37 R/f8-b8 (0:10.025) Rb8 0 1 0',
                 BLOCK_END]

        self.connection.process_lines(lines)
        self.assertEqual(self.connection.client.commands[-1], "moves 463")
                
        signal = 'obsGameCreated'
        lines = ['Movelist for game 463:',
                 '',
                'schachbjm (2243) vs. Maras (2158) --- Sat Jan 23, 14:34 EST 2016',
                'Rated standard match, initial time: 45 minutes, increment: 45 seconds.',
                '',
                'Move  schachbjm               Maras',
                '----  ---------------------   ---------------------',
                '1.  e4      (0:00.000)      e6      (0:00.000)',
                '2.  d4      (0:01.617)      d5      (0:02.220)',
                '3.  Nc3     (0:00.442)      Nc6     (0:54.807)',
                '4.  e5      (0:40.427)      Nge7    (0:28.205)',
                '5.  Nf3     (0:21.570)      Nf5     (0:28.818)',
                '6.  h4      (1:17.369)      h5      (4:58.315)',
                '7.  Bg5     (0:55.946)      Be7     (4:01.555)',
                '8.  Qd2     (0:02.434)      b6      (5:12.110)',
                '9.  O-O-O   (0:59.124)      Bb7     (0:08.796)',
                '10.  Kb1     (0:01.900)      Qd7     (4:39.500)',
                '11.  Bxe7    (19:59.514)     Qxe7    (2:42.462)',
                '12.  g3      (0:58.847)      O-O-O   (0:36.468)',
                '13.  Bh3     (0:12.284)      Nh6     (4:06.076)',
                '14.  Ne2     (0:02.387)      g6      (5:02.695)',
                '15.  Nf4     (0:02.976)      Kb8     (5:26.776)',
                '16.  Rhe1    (2:33.781)      Na5     (2:23.956)',
                '17.  b3      (0:28.817)      Rc8     (1:09.281)',
                '18.  Ng5     (8:15.515)      c5      (5:17.139)',
                '19.  Bxe6    (12:26.052)     fxe6    (1:14.670)',
                '20.  Nxg6    (0:02.168)      Qd7     (1:23.832)',
                '21.  Nxh8    (0:02.249)      Rxh8    (0:04.212)',
                '22.  dxc5    (0:14.456)      Nf5     (0:24.046)',
                '23.  cxb6    (0:07.092)      axb6    (0:03.296)',
                '24.  Qb4     (0:42.800)      Qc6     (2:48.991)',
                '25.  Nf7     (2:09.657)      Rc8     (0:37.030)',
                '26.  Rd2     (0:01.602)      Qc5     (5:03.082)',
                '27.  Qxc5    (0:09.672)      bxc5    (0:00.100)',
                '28.  Nd6     (0:00.849)      Rf8     (0:04.101)',
                '29.  c3      (0:57.437)      Kc7     (3:05.263)',
                '30.  Nxf5    (1:51.872)      Rxf5    (0:00.100)',
                '31.  f4      (0:00.603)      Bc6     (1:06.696)',
                '32.  Kc2     (0:01.613)      Be8     (0:07.670)',
                '33.  Kd3     (1:39.823)      Rf8     (1:28.227)',
                '34.  Ke3     (0:06.207)      Bg6     (0:08.648)',
                '35.  Rc1     (3:24.100)      Bf5     (1:11.762)',
                '36.  Rb2     (0:13.173)      Rb8     (0:10.025)',
                '{Still in progress} *',]
        
        game = FICSGame(FICSPlayer("schachbjm"), FICSPlayer("Maras"),
                gameno=463)
        game = self.connection.games.get(game)
        expectedResults = (game,)
        self.runAndAssertEquals(signal, lines, expectedResults)


class GamesTests(EmittingTestCase):
    def setUp (self):
        EmittingTestCase.setUp(self)
        self.manager = self.connection.games
    
    def test1 (self):
        """Make sure private game messages are caught"""
        lines = ["{Game 12 (VrtX vs. pulsoste) Creating rated crazyhouse match.}"]
        game = FICSGame(FICSPlayer('VrtX'), FICSPlayer('pulsoste'), gameno=12,
            rated=True, game_type=GAME_TYPES['crazyhouse'], private=False)
        self.runAndAssertEquals("FICSGameCreated", lines, ([game,],))
        
        lines = [BLOCK_START + '218' + BLOCK_SEPARATOR + '80' + BLOCK_SEPARATOR,
                 "Sorry, game 12 is a private game.",
                 BLOCK_END]
        game = self.connection.games[game]
        self.runAndAssertEqualsNotify(game, 'private', lines, True)

    def test2 (self):
        """ Make sure the correct draw reason was caught """
        lines = ["{Game 117 (Hevonen vs. narutochess) narutochess ran out of time and Hevonen has no material to mate} 1/2-1/2"]
        self.runAndAssertEqualPropValue("FICSGameEnded", lines, 'reason', DRAW_WHITEINSUFFICIENTANDBLACKTIME)

    def test3 (self):
        """ Make sure the correct draw reason was caught """
        lines = ["{Game 117 (Hevonen vs. narutochess) Hevonen ran out of time and narutochess has no material to mate} 1/2-1/2"]
        self.runAndAssertEqualPropValue("FICSGameEnded", lines, 'reason', DRAW_BLACKINSUFFICIENTANDWHITETIME)

    def test4 (self):
        """ Make sure the correct draw reason was caught """
        lines = ["{Game 117 (GuestBKKF vs. GuestTSNL) GuestBKKF ran out of time and GuestTSNL has no material to mate} 1/2-1/2"]
        self.runAndAssertEqualPropValue("FICSGameEnded", lines, 'reason', DRAW_BLACKINSUFFICIENTANDWHITETIME)

    def test5 (self):
        """ Make sure the correct draw reason was caught """
        lines = ["{Game 117 (GuestBKKF vs. GuestTSNL) GuestTSNL ran out of time and GuestBKKF has no material to mate} 1/2-1/2"]
        self.runAndAssertEqualPropValue("FICSGameEnded", lines, 'reason', DRAW_WHITEINSUFFICIENTANDBLACKTIME)

    def test6 (self):
        lines = ["{Game 84 (mgatto vs. JoseCapablanca) Game courtesyadjourned by mgatto} *"]
        self.runAndAssertEqualPropValue("FICSGameEnded", lines, 'reason', ADJOURNED_COURTESY_WHITE)

    def test7 (self):
        lines = ["{Game 84 (mgatto vs. JoseCapablanca) Game courtesyadjourned by JoseCapablanca} *"]
        self.runAndAssertEqualPropValue("FICSGameEnded", lines, 'reason', ADJOURNED_COURTESY_BLACK)
        
class HelperManagerTests(EmittingTestCase):
    def setUp (self):
        EmittingTestCase.setUp(self)
        self.manager = self.connection.hm
    
    def test1 (self):
        """ Make sure ratings <1000 are caught """
        lines = ["Artmachine Blitz ( 819), Std (1276), Wild (----), Light(----), Bug(----)",
                 "is now available for matches\."]
        player = self.connection.players.get(FICSPlayer('Artmachine'))
        self.runAndAssertEqualsNotify(player.ratings[TYPE_BLITZ], 'elo', lines,
                                      819)

class OfferManagerTests(EmittingTestCase):
    
    def setUp (self):
        EmittingTestCase.setUp(self)
        self.manager = self.connection.om
    
    def test1 (self):
        lines = ['<pf> 59 w=antiseptic t=match p=antiseptic (1945) mgatto (1729) rated wild 6 1 Loaded from wild/4 (adjourned)']
        player = FICSPlayer('antiseptic')
        player.ratings[TYPE_WILD].elo = 1945
        expectedResult = FICSChallenge(59, player, 6, 1, True, None,
                                       GAME_TYPES["wild/4"], adjourned=True)
        self.runAndAssertEquals('onChallengeAdd', lines, (expectedResult,))
        
    def test2 (self):
        lines = ['<pf> 71 w=joseph t=match p=joseph (1632) mgatto (1742) rated wild 5 1 Loaded from wild/fr (adjourned)']
        player = FICSPlayer('joseph')
        player.ratings[TYPE_WILD].elo = 1632
        expectedResult = FICSChallenge(71, player, 5, 1, True, None,
                                       GAME_TYPES["wild/fr"], adjourned=True)
        self.runAndAssertEquals('onChallengeAdd', lines, (expectedResult,))

    def test3 (self):
        lines = ['<pf> 45 w=GuestGYXR t=match p=GuestGYXR (----) Lobais (----) unrated losers 2 12']
        expectedResult = FICSChallenge(45, FICSPlayer('GuestGYXR'), 2, 12,
                                       False, None, GAME_TYPES["losers"])
        self.runAndAssertEquals('onChallengeAdd', lines, (expectedResult,))

    def test4 (self):
        lines = ['<pf> 39 w=GuestDVXV t=match p=GuestDVXV (----) GuestNXMP (----) unrated blitz 2 12 (adjourned)']
        expectedResult = FICSChallenge(39, FICSPlayer('GuestDVXV'), 2, 12,
                                       False, None, GAME_TYPES["blitz"],
                                       adjourned=True)
        self.runAndAssertEquals('onChallengeAdd', lines, (expectedResult,))

    def test5 (self):
        lines = ['<pf> 20 w=GuestFQPB t=match p=GuestFQPB (----) [white] mgatto (1322) unrated blitz 2 12']
        expectedResult = FICSChallenge(20, FICSPlayer('GuestFQPB'), 2, 12,
                                       False, "white", GAME_TYPES["blitz"])
        self.runAndAssertEquals('onChallengeAdd', lines, (expectedResult,))

    def test6 (self):
        lines = ['<pf> 7 w=GuestFQPB t=match p=GuestFQPB (----) [black] mgatto (----) unrated untimed']
        expectedResult = FICSChallenge(7, FICSPlayer('GuestFQPB'), 0, 0,
                                       False, "black", GAME_TYPES["untimed"])
        self.runAndAssertEquals('onChallengeAdd', lines, (expectedResult,))

class ConsoleManagerTests(EmittingTestCase):
    
    def setUp (self):
        EmittingTestCase.setUp(self)
        self.manager = self.connection.com
    
    def test1 (self):
        # id=0 needed here to let consolehandler work
        lines = [BLOCK_START + '0' + BLOCK_SEPARATOR + '37' + BLOCK_SEPARATOR,
                 "Finger of mgatto:",
                 "",
                 "On for: 44 mins   Idle: 0 secs",
                 "",
                 "rating     RD      win    loss    draw   total   best",
                 "Blitz      1343     51.5     937     781      58    1776   1729 (20-Feb-2000)",
                 "Standard   1685    332.0      56      39       7     102   1813 (03-Sep-2004)",
                 "Lightning  1269     64.4     653     718      32    1403   1873 (30-Jan-2000)",
                 "Crazyhouse 1332    191.4       0       3       0       3",
                 "Suicide    1254    350.0       0       3       0       3",
                 "Atomic     1290    184.6       1       8       0       9",
                 "",
                 "Email      : mattgatto@gmail.com",
                 "",
                 "Total time online: 64 days, 20 hrs, 58 mins",
                 "% of life online:  1.3  (since Sun Oct  3, 13:12 PDT 1999)",
                 "",
                 "Timeseal 1 : On",
                 "",
                 "1: I live in San Francisco and drive a taxi here",
                 "2: If you're using Linux check out pychess: http://www.pychess.org",
                 BLOCK_END]
        expected_result = [TelnetLine(line, 37) for line in lines[1:-1]]
        expected_result.append(TelnetLine('', 37))
        self.runAndAssertEquals("consoleMessage", lines, (expected_result, None))

if __name__ == '__main__':
    unittest.main()

import asyncio
import re
import sys
import socket
import traceback
from collections import defaultdict
from concurrent.futures import CancelledError

from gi.repository import GObject

import pychess
from pychess.compat import create_task
from pychess.System.Log import log

from pychess import ic
from pychess.Utils.const import NAME, FISCHERRANDOMCHESS, LOSERSCHESS, ATOMICCHESS, CRAZYHOUSECHESS
from .managers.SeekManager import SeekManager
from .managers.FingerManager import FingerManager
from .managers.NewsManager import NewsManager
from .managers.BoardManager import BoardManager
from .managers.OfferManager import OfferManager
from .managers.ChatManager import ChatManager
from .managers.ConsoleManager import ConsoleManager
from .managers.HelperManager import HelperManager
from .managers.ListAndVarManager import ListAndVarManager
from .managers.AutoLogOutManager import AutoLogOutManager
from .managers.ErrorManager import ErrorManager
from .managers.AdjournManager import AdjournManager
from .managers.ICCSeekManager import ICCSeekManager
from .managers.ICCBoardManager import ICCBoardManager
from .managers.ICCChatManager import ICCChatManager
from .managers.ICCHelperManager import ICCHelperManager
from .managers.ICCAdjournManager import ICCAdjournManager
from .managers.ICCErrorManager import ICCErrorManager
from .managers.ICCFingerManager import ICCFingerManager
from .managers.ICCListAndVarManager import ICCListAndVarManager
from .managers.ICCNewsManager import ICCNewsManager
from .managers.ICCOfferManager import ICCOfferManager
from .managers.ICCAutoLogOutManager import ICCAutoLogOutManager

from .FICSObjects import FICSPlayers, FICSGames, FICSSeeks, FICSChallenges
from .TimeSeal import CanceledException, ICSTelnet
from .VerboseTelnet import LinePrediction, FromPlusPrediction, FromABPlusPrediction, \
    FromToPrediction, PredictionsTelnet, NLinesPrediction


class LogOnException(Exception):
    pass


class Connection(GObject.GObject):

    __gsignals__ = {
        'connecting': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'connectingMsg': (GObject.SignalFlags.RUN_FIRST, None, (str, )),
        'connected': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'disconnected': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'error': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
    }

    def __init__(self, host, ports, timeseal, username, password):
        GObject.GObject.__init__(self)
        self.daemon = True
        self.host = host
        self.ports = ports
        self.username = username
        self.password = password
        self.timeseal = timeseal

        self.connected = False
        self.connecting = False
        self.keep_alive_task = None

        self.predictions = set()
        self.predictionsDict = {}
        self.reply_cmd_dict = defaultdict(list)

        # Are we connected to FatICS ?
        self.FatICS = False

        self.USCN = False

        self.ICC = False
        self.replay_dg_dict = {}
        self.replay_cn_dict = {}

    @property
    def ics_name(self):
        if self.FatICS:
            return "FatICS"
        elif self.USCN:
            return "USCN"
        elif self.ICC:
            return "ICC"
        else:
            return "FICS"

    def expect(self, prediction):
        self.predictions.add(prediction)
        self.predictionsDict[prediction.callback] = prediction
        if hasattr(prediction.callback, "BLKCMD"):
            predictions = self.reply_cmd_dict[prediction.callback.BLKCMD]
            predictions.append(prediction)
            # Do reverse sorted so we can later test the longest predictions first.
            # This is so that matching prefers the longest match for matches
            # that start out with the same regexp line(s)
            self.reply_cmd_dict[prediction.callback.BLKCMD] = sorted(
                predictions,
                key=len,
                reverse=True)

    def unexpect(self, callback):
        self.predictions.remove(self.predictionsDict.pop(callback))
        if hasattr(callback, "BLKCMD"):
            for prediction in self.reply_cmd_dict[callback.BLKCMD]:
                if prediction.callback == callback:
                    self.reply_cmd_dict[callback.BLKCMD].remove(prediction)
            if len(self.reply_cmd_dict[callback.BLKCMD]) == 0:
                del self.reply_cmd_dict[callback.BLKCMD]

    def expect_dg_line(self, number, callback):
        self.replay_dg_dict[number] = callback

    def expect_cn_line(self, number, callback):
        self.replay_cn_dict[number] = callback

    def expect_line(self, callback, regexp):
        self.expect(LinePrediction(callback, regexp))

    def expect_n_lines(self, callback, *regexps):
        self.expect(NLinesPrediction(callback, *regexps))

    def expect_fromplus(self, callback, regexp0, regexp1):
        self.expect(FromPlusPrediction(callback, regexp0, regexp1))

    def expect_fromABplus(self, callback, regexp0, regexp1, regexp2):
        self.expect(FromABPlusPrediction(callback, regexp0, regexp1, regexp2))

    def expect_fromto(self, callback, regexp0, regexp1):
        self.expect(FromToPrediction(callback, regexp0, regexp1))

    def cancel(self):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()

    def getUsername(self):
        return self.username

    def isRegistred(self):
        return self.password is not None and self.password != ""

    def isConnected(self):
        return self.connected

    def isConnecting(self):
        return self.connecting


EOF = _("The connection was broken - got \"end of file\" message")
NOTREG = _("'%s' is not a registered name")
BADPAS = _("The entered password was invalid.\n" +
           "If you forgot your password, go to " +
           "<a href=\"http://www.freechess.org/password\">" +
           "http://www.freechess.org/password</a> to request a new one over email.")
ALREADYIN = _("Sorry '%s' is already logged in")
REGISTERED = _(
    "'%s' is a registered name.  If it is yours, type the password.")
PREVENTED = _("Due to abuse problems, guest connections have been prevented.\n" +
              "You can still register on http://www.freechess.org")


class FICSConnection(Connection):
    def __init__(self, host, ports, timeseal, username="guest", password=""):
        Connection.__init__(self, host, ports, timeseal, username, password)

    def _post_connect_hook(self, lines):
        pass

    def _start_managers(self):
        pass

    @asyncio.coroutine
    def _connect(self):
        self.connecting = True
        self.emit("connecting")
        try:

            self.emit('connectingMsg', _("Connecting to server"))
            for i, port in enumerate(self.ports):
                log.debug("Trying port %d" % port,
                          extra={"task": (self.host, "raw")})
                try:
                    connected_event = asyncio.Event()
                    self.client = ICSTelnet(self.timeseal)
                    create_task(self.client.start(self.host, port, connected_event))
                    yield from connected_event.wait()
                except socket.error as err:
                    log.debug("Failed to open port %d %s" % (port, err),
                              extra={"task": (self.host, "raw")})
                    if i + 1 == len(self.ports):
                        raise
                    else:
                        continue
                else:
                    break

            yield from self.client.read_until("login: ")
            self.emit('connectingMsg', _("Logging on to server"))

            # login with registered handle
            if self.password:
                self.client.write(self.username)
                got = yield from self.client.read_until(
                    "password:", "enter the server as", "Try again.")
                if got == 0:
                    self.client.sensitive = True
                    self.client.write(self.password)
                # No such name
                elif got == 1:
                    raise LogOnException(NOTREG % self.username)
                # Bad name
                elif got == 2:
                    raise LogOnException(NOTREG % self.username)
            else:
                if self.username:
                    self.client.write(self.username)
                else:
                    self.client.write("guest")
                got = yield from self.client.read_until(
                    "Press return",
                    "You are connected as a guest",
                    "If it is yours, type the password.",
                    "guest connections have been prevented",
                    "nobody from your site may login without an account.")
                # got = 3
                if got == 2:
                    raise LogOnException(REGISTERED % self.username)
                elif got == 3 or got == 4:
                    raise LogOnException(PREVENTED)
                self.client.write("")

            while True:
                line = yield from self.client.readline()
                if "Invalid password" in line:
                    raise LogOnException(BADPAS)
                elif "is already logged in" in line:
                    raise LogOnException(ALREADYIN % self.username)

                match = re.search(
                    "\*\*\*\* Starting FICS session as " + "(%s)%s \*\*\*\*" %
                    (ic.NAMES_RE, ic.TITLES_RE), line)
                if match:
                    self.username = match.groups()[0]
                    break

                # USCN specific line
                match = re.search("Created temporary login '(%s)'" % ic.NAMES_RE, line)
                if match:
                    self.username = match.groups()[0]
                    break

                match = re.search("For a list of events, click here:", line)
                if match:
                    break

                # ICC specific line
                match = re.search("help anonymous", line)
                if match:
                    break

                match = re.search("This is the admin message of the day", line)
                if match:
                    break

            self.emit('connectingMsg', _("Setting up environment"))
            lines = yield from self.client.readuntil(b"ics%")
            self._post_connect_hook(lines)
            self.FatICS = self.client.FatICS
            self.USCN = self.client.USCN
            self.ICC = self.client.ICC
            self.client.name = self.username
            self.client = PredictionsTelnet(self.client, self.predictions, self.reply_cmd_dict,
                                            self.replay_dg_dict, self.replay_cn_dict)
            self.client.lines.line_prefix = "aics%" if self.ICC else "fics%"

            if not self.USCN and not self.ICC:
                self.client.run_command("iset block 1")
                self.client.lines.block_mode = True

            if self.ICC:
                self.client.run_command("set level1 5")
                self.client.run_command("set prompt 0")
                self.client.lines.datagram_mode = True

                ic.GAME_TYPES_BY_SHORT_FICS_NAME["B"] = ic.GAME_TYPES["bullet"]
                ic.VARIANT_GAME_TYPES[ATOMICCHESS] = ic.GAME_TYPES["w27"]
                ic.VARIANT_GAME_TYPES[CRAZYHOUSECHESS] = ic.GAME_TYPES["w23"]
                ic.VARIANT_GAME_TYPES[LOSERSCHESS] = ic.GAME_TYPES["w17"]
                ic.VARIANT_GAME_TYPES[FISCHERRANDOMCHESS] = ic.GAME_TYPES["w22"]
            else:
                ic.GAME_TYPES_BY_SHORT_FICS_NAME["B"] = ic.GAME_TYPES["bughouse"]
                ic.VARIANT_GAME_TYPES[ATOMICCHESS] = ic.GAME_TYPES["atomic"]
                ic.VARIANT_GAME_TYPES[CRAZYHOUSECHESS] = ic.GAME_TYPES["crazyhouse"]
                ic.VARIANT_GAME_TYPES[LOSERSCHESS] = ic.GAME_TYPES["losers"]
                ic.VARIANT_GAME_TYPES[FISCHERRANDOMCHESS] = ic.GAME_TYPES["wild/fr"]

            self.client.run_command("iset defprompt 1")
            self.client.run_command("iset ms 1")

            self._start_managers(lines)
            self.connecting = False
            self.connected = True
            self.emit("connected")

            @asyncio.coroutine
            def keep_alive():
                while self.isConnected():
                    self.client.run_command("date")
                    yield from asyncio.sleep(30 * 60)
            self.keep_alive_task = create_task(keep_alive())

        except CanceledException as err:
            log.info("FICSConnection._connect: %s" % repr(err),
                     extra={"task": (self.host, "raw")})
        finally:
            self.connecting = False

    @asyncio.coroutine
    def start(self):
        try:
            if not self.isConnected():
                yield from self._connect()
            while self.isConnected():
                yield from self.client.parse()
        except CancelledError:
            pass
        except Exception as err:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            log.info("FICSConnection.run: %s" % repr(err),
                     extra={"task": (self.host, "raw")})
            self.close()
            if isinstance(err,
                          (IOError, LogOnException, EOFError, socket.error,
                           socket.gaierror, socket.herror)):
                self.emit("error", err)
            else:
                raise
        finally:
            if isinstance(self, FICSMainConnection):
                self.emit("disconnected")

    def cancel(self):
        self.close()
        if hasattr(self, "client"):
            self.client.cancel()

    def close(self):
        self.connected = False
        if hasattr(self, "client"):
            self.client.close()
        if self.keep_alive_task is not None:
            self.keep_alive_task.cancel()


class FICSMainConnection(FICSConnection):
    def __init__(self, host, ports, timeseal, username="guest", password=""):
        FICSConnection.__init__(self, host, ports, timeseal, username, password)
        self.lvm = None
        self.notify_users = []
        self.ini_messages = []
        self.players = FICSPlayers(self)
        self.games = FICSGames(self)
        self.seeks = FICSSeeks(self)
        self.challenges = FICSChallenges(self)
        self.archived_examine = None
        self.examined_game = None
        self.stored_owner = self.username
        self.history_owner = self.username
        self.journal_owner = self.username
        self.set_user_vars = False

    def close(self):
        if isinstance(self.client, PredictionsTelnet) and self.set_user_vars:
            self.client.run_command("set open 0")
            self.client.run_command("set gin 0")
            self.client.run_command("set availinfo 0")
        try:
            self.lvm.stop()
        except AttributeError:
            pass
        except Exception as err:
            if not isinstance(err,
                              (IOError, LogOnException, EOFError, socket.error,
                               socket.gaierror, socket.herror)):
                raise
        finally:
            FICSConnection.close(self)

    def _post_connect_hook(self, lines):
        self.ini_messages = lines.splitlines()
        notify_users = re.search("Present company includes: ((?:%s ?)+)\." %
                                 ic.NAMES_RE, lines)
        if notify_users:
            self.notify_users.extend(notify_users.groups()[0].split())

    def _start_managers(self, lines):
        self.client.run_command("set interface %s %s" %
                                (NAME, pychess.VERSION))

        # FIXME: Some managers use each other to avoid regexp collapse. To
        # avoid having to init the in a specific order, connect calls should
        # be moved to a "start" function, so all managers would be in
        # the connection object when they are called
        if self.ICC:
            self.lvm = ICCListAndVarManager(self)
            self.em = ICCErrorManager(self)
            self.glm = ICCSeekManager(self)
            self.bm = ICCBoardManager(self)
            self.cm = ICCChatManager(self)
            self.adm = ICCAdjournManager(self)
            self.fm = ICCFingerManager(self)
            self.nm = ICCNewsManager(self)
            self.om = ICCOfferManager(self)
            self.alm = ICCAutoLogOutManager(self)
        else:
            self.lvm = ListAndVarManager(self)
            self.em = ErrorManager(self)
            self.glm = SeekManager(self)
            self.bm = BoardManager(self)
            self.cm = ChatManager(self)
            self.adm = AdjournManager(self)
            self.fm = FingerManager(self)
            self.nm = NewsManager(self)
            self.om = OfferManager(self)
            self.alm = AutoLogOutManager(self)
        self.com = ConsoleManager(self)
        self.bm.start()
        self.players.start()
        self.games.start()
        self.seeks.start()
        self.challenges.start()

        # This block may useful if one wants to create
        # unit test lines from real life fics output
        if False:
            self.client.run_command("set seek 0")
            self.client.run_command("set shout 0")
            self.client.run_command("set cshout 0")
            self.client.run_command("iset seekinfo 0")
            self.client.run_command("iset seekremove 0")
            self.client.run_command("iset showownseek 0")
            self.client.run_command("iset allresults 0")
            self.client.run_command("iset pin 0")
            self.client.run_command("set open 0")
            self.client.run_command("set gin 0")
            self.client.run_command("set availinfo 0")

    def start_helper_manager(self, set_user_vars):
        # if guest accounts disabled we will handle players in the main connection
        if self.FatICS or self.USCN or self.ICC:
            self.client.run_command("set pin 1")
        else:
            self.client.run_command("iset allresults 1")
            # ivar pin: http://www.freechess.org/Help/HelpFiles/new_features.html
            self.client.run_command("iset pin 1")

        self.set_user_vars = set_user_vars
        if self.set_user_vars:
            self.client.run_command("set open 1")
            self.client.run_command("set gin 1")
            self.client.run_command("set availinfo 1")
        if self.ICC:
            self.hm = ICCHelperManager(self, self)
        else:
            self.hm = HelperManager(self, self)

        # disable setting iveriables from console
        self.client.run_command("iset lock 1")


class FICSHelperConnection(FICSConnection):
    def __init__(self, main_conn, host, ports, timeseal, username="guest", password=""):
        FICSConnection.__init__(self, host, ports, timeseal, username, password)
        self.main_conn = main_conn

    def _start_managers(self, lines):
        # The helper just wants only player and game notifications
        # set open 1 is a requirement for availinfo notifications
        self.client.run_command("set open 1")
        self.client.run_command("set seek 0")
        self.client.run_command("set shout 0")
        self.client.run_command("set cshout 0")
        self.client.run_command("set tell 0")
        self.client.run_command("set chanoff 1")
        self.client.run_command("set gin 1")
        self.client.run_command("set availinfo 1")
        if self.FatICS or self.USCN or self.ICC:
            self.client.run_command("set pin 1")
        else:
            self.client.run_command("iset allresults 1")
            # ivar pin: http://www.freechess.org/Help/HelpFiles/new_features.html
            self.client.run_command("iset pin 1")
        self.hm = HelperManager(self, self.main_conn)

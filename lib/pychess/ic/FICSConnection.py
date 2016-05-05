from __future__ import absolute_import, print_function

import re
import socket
import time
import threading
from threading import Event, Thread
from collections import defaultdict

from gi.repository import GObject

import pychess
from pychess.System import fident
from pychess.System.Log import log

from pychess.ic import NAMES_RE, TITLES_RE
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
from pychess.Utils.const import NAME

from .FICSObjects import FICSPlayers, FICSGames, FICSSeeks, FICSChallenges
from .TimeSeal import TimeSeal, CanceledException
from .VerboseTelnet import LinePrediction, FromPlusPrediction, FromABPlusPrediction, \
    FromToPrediction, PredictionsTelnet, NLinesPrediction


class LogOnException(Exception):
    pass


class Connection(GObject.GObject, Thread):

    __gsignals__ = {
        'connecting': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'connectingMsg': (GObject.SignalFlags.RUN_FIRST, None, (str, )),
        'connected': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'disconnected': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'error': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
    }

    def __init__(self, host, ports, username, password):
        GObject.GObject.__init__(self)
        Thread.__init__(self, name=fident(self.run))
        self.daemon = True
        self.host = host
        self.ports = ports
        self.username = username
        self.password = password

        self.connected = False
        self.connecting = False

        self.predictions = set()
        self.predictionsDict = {}
        self.reply_cmd_dict = defaultdict(list)

        # Are we connected to FatICS ?
        self.FatICS = False

        self.USCN = False

    @property
    def ics_name(self):
        if self.FatICS:
            return "FatICS"
        elif self.USCN:
            return "USCN"
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
    def __init__(self, host, ports, username="guest", password=""):
        Connection.__init__(self, host, ports, username, password)

    def _post_connect_hook(self, lines):
        pass

    def _start_managers(self):
        pass

    def _connect(self):
        self.connecting = True
        self.emit("connecting")
        try:
            self.client = TimeSeal()

            self.emit('connectingMsg', _("Connecting to server"))
            for i, port in enumerate(self.ports):
                log.debug("Trying port %d" % port,
                          extra={"task": (self.host, "raw")})
                try:
                    self.client.open(self.host, port)
                except socket.error as err:
                    log.debug("Failed to open port %d %s" % (port, err),
                              extra={"task": (self.host, "raw")})
                    if i + 1 == len(self.ports):
                        raise
                    else:
                        continue
                else:
                    break

            self.client.read_until("login: ")
            self.emit('connectingMsg', _("Logging on to server"))

            # login with registered handle
            if self.password:
                print(self.username, file=self.client)
                got = self.client.read_until(
                    "password:", "enter the server as", "Try again.")
                if got == 0:
                    self.client.sensitive = True
                    print(self.password, file=self.client)
                # No such name
                elif got == 1:
                    raise LogOnException(NOTREG % self.username)
                # Bad name
                elif got == 2:
                    raise LogOnException(NOTREG % self.username)
            else:
                if self.username:
                    print(self.username, file=self.client)
                else:
                    print("guest", file=self.client)
                got = self.client.read_until(
                    "Press return",
                    "If it is yours, type the password.",
                    "guest connections have been prevented",
                    "nobody from your site may login without an account.")
                # got = 3
                if got == 1:
                    raise LogOnException(REGISTERED % self.username)
                elif got == 2 or got == 3:
                    raise LogOnException(PREVENTED)
                print(file=self.client)

            while True:
                line = self.client.readline()
                if "Invalid password" in line:
                    raise LogOnException(BADPAS)
                elif "is already logged in" in line:
                    raise LogOnException(ALREADYIN % self.username)

                match = re.search(
                    "\*\*\*\* Starting FICS session as " + "(%s)%s \*\*\*\*" %
                    (NAMES_RE, TITLES_RE), line)
                if match:
                    self.username = match.groups()[0]
                    break

                    # USCN specific lines
                match = re.search("Created temporary login '(%s)'" % NAMES_RE,
                                  line)
                if match:
                    self.username = match.groups()[0]
                    break
                match = re.search("answers to frequently asked questions",
                                  line)
                if match:
                    break
                match = re.search("This is the admin message of the day", line)
                if match:
                    break

            self.emit('connectingMsg', _("Setting up environment"))
            lines = self.client.readuntil(b"ics%")
            self._post_connect_hook(lines)
            self.FatICS = self.client.FatICS
            self.USCN = self.client.USCN
            self.client.name = self.username
            self.client = PredictionsTelnet(self.client, self.predictions,
                                            self.reply_cmd_dict)
            self.client.lines.line_prefix = "fics%"
            if not self.USCN:
                self.client.run_command("iset block 1")
                self.client.lines.block_mode = True
            self.client.run_command("iset defprompt 1")
            self.client.run_command("iset ms 1")

            self._start_managers(lines)
            self.connecting = False
            self.connected = True
            self.emit("connected")

            def keep_alive():
                last = time.time()
                while self.isConnected():
                    if time.time() - last > 59 * 60:
                        self.client.run_command("date")
                        last = time.time()
                    time.sleep(30)

            thread = threading.Thread(target=keep_alive, name=fident(keep_alive))
            thread.daemon = True
            thread.start()

        except CanceledException as err:
            log.info("FICSConnection._connect: %s" % repr(err),
                     extra={"task": (self.host, "raw")})
        finally:
            self.connecting = False

    def run(self):
        try:
            try:
                if not self.isConnected():
                    self._connect()
                while self.isConnected():
                    self.client.parse()
            except Exception as err:
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
            self.emit("disconnected")

    def cancel(self):
        self.close()
        self.client.cancel()

    def close(self):
        self.connected = False
        self.client.close()


class FICSMainConnection(FICSConnection):
    def __init__(self, host, ports, username="guest", password=""):
        FICSConnection.__init__(self, host, ports, username, password)
        self.lvm = None
        self.notify_users = []
        self.ini_messages = []
        self.lounge_loaded = Event()
        self.players = FICSPlayers(self)
        self.games = FICSGames(self)
        self.seeks = FICSSeeks(self)
        self.challenges = FICSChallenges(self)
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
                                 NAMES_RE, lines)
        if notify_users:
            self.notify_users.extend(notify_users.groups()[0].split(" "))

    def _start_managers(self, lines):
        self.client.run_command("set interface %s %s" %
                                (NAME, pychess.VERSION))

        # FIXME: Some managers use each other to avoid regexp collapse. To
        # avoid having to init the in a specific order, connect calls should
        # be moved to a "start" function, so all managers would be in
        # the connection object when they are called
        self.lvm = ListAndVarManager(self)
        self.em = ErrorManager(self)
        self.glm = SeekManager(self)
        self.bm = BoardManager(self)
        self.fm = FingerManager(self)
        self.nm = NewsManager(self)
        self.om = OfferManager(self)
        self.cm = ChatManager(self)
        self.alm = AutoLogOutManager(self)
        self.adm = AdjournManager(self)
        self.com = ConsoleManager(self)
        self.bm.start()
        self.players.start()
        self.games.start()
        self.seeks.start()
        self.challenges.start()

    def start_helper_manager(self, set_user_vars):
        # if guest accounts disabled we will handle players in the main connection
        if self.FatICS or self.USCN:
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
        self.hm = HelperManager(self, self)

        # disable setting iveriables from console
        self.client.run_command("iset lock 1")


class FICSHelperConnection(FICSConnection):
    def __init__(self, main_conn, host, ports, username="guest", password=""):
        FICSConnection.__init__(self, host, ports, username, password)
        self.main_conn = main_conn

    def _start_managers(self, lines):
        # The helper just wants only player and game notifications
        self.main_conn.lounge_loaded.wait()
        # set open 1 is a requirement for availinfo notifications
        self.client.run_command("set open 1")
        self.client.run_command("set seek 0")
        self.client.run_command("set shout 0")
        self.client.run_command("set cshout 0")
        self.client.run_command("set tell 0")
        self.client.run_command("set chanoff 1")
        self.client.run_command("set gin 1")
        self.client.run_command("set availinfo 1")
        if self.FatICS or self.USCN:
            self.client.run_command("set pin 1")
        else:
            self.client.run_command("iset allresults 1")
            # ivar pin: http://www.freechess.org/Help/HelpFiles/new_features.html
            self.client.run_command("iset pin 1")
        self.hm = HelperManager(self, self.main_conn)

        # disable setting iveriables from console
        self.main_conn.client.run_command("iset lock 1")

import re, socket

from gobject import GObject, SIGNAL_RUN_FIRST

from pychess.System.Log import log
from pychess.System.ThreadPool import PooledThread
from pychess.Utils.const import *

_ = lambda x:x

from managers.GameListManager import GameListManager
from managers.FingerManager import FingerManager
from managers.NewsManager import NewsManager
from managers.BoardManager import BoardManager
from managers.OfferManager import OfferManager
from managers.ChatManager import ChatManager
from managers.ListAndVarManager import ListAndVarManager
from managers.AutoLogOutManager import AutoLogOutManager
from managers.ErrorManager import ErrorManager
from managers.AdjournManager import AdjournManager

from TimeSeal import TimeSeal
from VerboseTelnet import LinePrediction
from VerboseTelnet import ManyLinesPrediction
from VerboseTelnet import FromPlusPrediction
from VerboseTelnet import FromToPrediction
from VerboseTelnet import PredictionsTelnet
from VerboseTelnet import NLinesPrediction

class LogOnError (StandardError): pass

class Connection (GObject, PooledThread):
    
    __gsignals__ = {
        'connecting':    (SIGNAL_RUN_FIRST, None, ()),
        'connectingMsg': (SIGNAL_RUN_FIRST, None, (str,)),
        'connected':     (SIGNAL_RUN_FIRST, None, ()),
        'disconnecting': (SIGNAL_RUN_FIRST, None, ()),
        'disconnected':  (SIGNAL_RUN_FIRST, None, ()),
        'error':         (SIGNAL_RUN_FIRST, None, (object,)),
    }
    
    def __init__ (self, host, ports, username, password):
        GObject.__init__(self)
        
        self.host = host
        self.ports = ports
        self.username = username
        self.password = password
        
        self.connected = False
        self.connecting = False
        
        self.predictions = set()
        self.predictionsDict = {}
    
    def expect (self, prediction):
        self.predictions.add(prediction)
        self.predictionsDict[prediction.callback] = prediction
    
    def unexpect (self, callback):
        self.predictions.remove(self.predictionsDict.pop(callback))
    
    def expect_line (self, callback, regexp):
        self.expect(LinePrediction(callback, regexp))
    
    def expect_many_lines (self, callback, regexp):
        self.expect(ManyLinesPrediction(callback, regexp))
    
    def expect_n_lines (self, callback, *regexps):
        self.expect(NLinesPrediction(callback, *regexps))
    
    def expect_line_plus (self, callback, regexp):
        def callback_decorator (matchlist):
            callback([matchlist[0]]+[m.group(0) for m in matchlist[1:]])
        self.expect(FromPlusPrediction(callback_decorator, regexp, "\   (.*)"))
    
    def expect_fromplus (self, callback, regexp0, regexp1):
        self.expect(FromPlusPrediction(callback, regexp0, regexp1))
    
    def expect_fromto (self, callback, regexp0, regexp1):
        self.expect(FromToPrediction(callback, regexp0, regexp1))
    
    
    def cancel (self):
        raise NotImplementedError()
    
    def disconnect (self):
        raise NotImplementedError()
    
    def getUsername (self):
        return self.username
    
    def isRegistred (self):
        return self.password
    
    def isConnected (self):
        return self.connected
    
    def isConnecting (self):
        return self.connecting


EOF = _("The connection was broken - got \"end of file\" message")
NOTREG = _("'%s' is not a registered name")
BADPAS = _("The entered password was invalid.\n" + \
           "If you have forgot your password, try logging in as a guest and open chat on channel 4. Write \"I've forgotten my password\" to get help.\n"+\
           "If that is by some reason not possible, please email: support@freechess.org")

class FICSConnection (Connection):
    def __init__ (self, host, ports, username="guest", password=""):
        Connection.__init__(self, host, ports, username, password)
        self.registred = None
    
    def _connect (self):
        self.connecting = True
        self.emit("connecting")
        try:
            self.client = TimeSeal()
            
            self.emit('connectingMsg', _("Connecting to server"))
            for i, port in enumerate(self.ports):
                log.debug("Trying port %d\n" % port, (self.host, "raw"))
                try:
                    self.client.open(self.host, port)
                except socket.error, e:
                    if e.args[0] != 111 or i+1 == len(self.ports):
                        raise
                else:
                    break
            
            self.client.read_until("login: ")
            self.emit('connectingMsg', _("Logging on to server"))
            
            if self.username and self.username != "guest":
                print >> self.client, self.username
                got = self.client.read_until("password:",
                                             "enter the server as",
                                             "Try again.")
                if got == 0:
                    print >> self.client, self.password
                    self.registred = True
                # No such name
                elif got == 1:
                    raise LogOnError, NOTREG % self.username
                # Bad name
                elif got == 2:
                    raise LogOnError, NOTREG % self.username
            else:
                print >> self.client, "guest"
                self.client.read_until("Press return")
                print >> self.client
                self.registred = False
            
            while True:
                line = self.client.readline()
                if "Invalid password" in line:
                    raise LogOnError, BADPAS
                
                match = re.search("\*\*\*\* Starting FICS session as "+
                                  "([A-Za-z]+)(?:\([A-Z*]+\))* \*\*\*\*", line)
                if match:
                    self.username = match.groups()[0]
                    break
            
            self.client.readuntil("fics%")
            
            self.emit('connectingMsg', _("Setting up enviroment"))
            self.client = PredictionsTelnet(self.client)
            self.client.setStripLines(True)
            self.client.setLinePrefix("fics%")
            
            # Important: As the other managers use ListAndVarManager, we need it
            # to be instantiated first. We might decide that the purpose of this
            # manager is different - used by different parts of the code - so it
            # should be implemented into the FICSConnection somehow.
            self.lvm = ListAndVarManager(self)
            while not self.lvm.isReady():
                self.client.handleSomeText(self.predictions)
            self.lvm.setVariable("interface", NAME+" "+VERSION)
            
            # FIXME: Some managers use each other to avoid regexp collapse. To
            # avoid having to init the in a specific order, connect calls should
            # be moved to a "start" function, so all managers would be in
            # the connection object when they are called
            self.em = ErrorManager(self)
            self.glm = GameListManager(self)
            self.bm = BoardManager(self)
            self.fm = FingerManager(self)
            self.nm = NewsManager(self)
            self.om = OfferManager(self)
            self.cm = ChatManager(self)
            self.alm = AutoLogOutManager(self)
            self.adm = AdjournManager(self)
            
            self.connecting = False
            self.connected = True
            self.emit("connected")
        
        finally:
            self.connecting = False
    
    def run (self):
        try:
            if not self.isConnected():
                self._connect()
            while self.isConnected():
                self.client.handleSomeText(self.predictions)
        
        except Exception, e:
            if self.connected:
                self.connected = False
            for errortype in (IOError, LogOnError, EOFError,
                              socket.error, socket.gaierror, socket.herror):
                if isinstance(e, errortype):
                    self.emit("error", e)
                    break
            else:
                raise
        
        self.emit("disconnected")
    
    def disconnect (self):
        self.emit("disconnecting")
        if self.isConnected():
            print >> self.client, "quit"
            self.connected = False
        self.client.close()
    
    def isRegistred (self):
        assert self.registred != None
        return self.registred
    
    def getUsername (self):
        assert self.username != None
        return self.username

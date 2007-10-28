import re, socket

from gobject import GObject, SIGNAL_RUN_FIRST

from VerboseTelnet import *

from managers.GameListManager import GameListManager
from managers.FingerManager import FingerManager
from managers.NewsManager import NewsManager
from managers.BoardManager import BoardManager
from managers.OfferManager import OfferManager

from pychess.System.ThreadPool import PooledThread

class LogOnError (StandardError): pass

class Connection (GObject, PooledThread):
    
    __gsignals__ = {
        'connecting':    (SIGNAL_RUN_FIRST, None, ()),
        'connected':     (SIGNAL_RUN_FIRST, None, ()),
        'disconnecting': (SIGNAL_RUN_FIRST, None, ()),
        'disconnected':  (SIGNAL_RUN_FIRST, None, ()),
        'error':         (SIGNAL_RUN_FIRST, None, (object,)),
    }
    
    def __init__ (self, host, port, username, password):
        GObject.__init__(self)
        
        self.host = host
        self.port = port
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
        self.expect(Prediction(READ_LINE, callback, regexp))
    
    def expect_line_plus (self, callback, regexp):
        self.expect(Prediction(READ_LINE_PLUS, callback, regexp))
    
    def expect_fromto (self, callback, regexp0, regexp1):
        self.expect(Prediction(READ_FROMTO, callback, regexp0, regexp1))
    
    
    
    def cancel (self):
        raise NotImplementedError()
    
    def disconnect (self):
        raise NotImplementedError()
    
    def getUsername (self):
        raise NotImplementedError()
    
    def isRegistred (self):
        raise NotImplementedError()
    
    def isConnected (self):
        return self.connected
    
    def isConnecting (self):
        return self.connecting

EOF = _("The connection was broken - got \"end of file\" message")
NOTREG = _("'%s' is not a registered name")
BADPAS = _("The entered password was invalid.\n\n" + \
           "If you have forgot your password, try logging in as a guest and open chat on channel 4. Write \"I've forgotten my password\" to get help.\n\n"+\
           "If that is by some reason not possible, please email: support@freechess.org")

# Some errorstrings for gnugettext to find. Add more as fics spits them out
_("Sorry, names can only consist of lower and upper case letters.")
_("Sorry, names may be at most 17 characters long.")

class FICSConnection (Connection):
    def __init__ (self, host, port, username="guest", password=""):
        Connection.__init__(self, host, port, username, password)
        self.registred = None
    
    def _connect (self):
        self.connecting = True
        self.emit("connecting")
        try:
            self.client = VerboseTelnet()
            
            self.client.open(self.host, self.port)
            
            self.client.read_until("login: ")
            
            if self.username and self.username != "guest":
                print >> self.client, self.username
                index, match, text = self.client.expect([
                        "password: .*",
                        "login: .*",
                        "\n(.*?)Try again\..*",
                        "Press return to enter the server as.*"])
                if index < 0:
                    raise IOError, EOF
                elif index == 0:
                    print >> self.client, self.password
                    self.registred = True
                elif index == 2:
                    raise LogOnError, _(match.groups()[0].strip())
                elif index == 3:
                    raise LogOnError, NOTREG % self.username
            
            else:
                print >> self.client, "guest"
                self.client.read_until("Press return")
                print >> self.client
                self.registred = False
            
            index, match, text = self.client.expect([
                    "Invalid password",
                    "Starting FICS session as (\w+)(?:\(([CUHIFWM])\))?"])
            
            if index == 0:
                raise LogOnError, BADPAS
            elif index == 1:
                self.username = match.groups()[0]
            
            self.client.read_until("fics%")
            
            self.glm = GameListManager(self)
            self.fm = FingerManager(self)
            self.nm = NewsManager(self)
            self.bm = BoardManager(self)
            self.om = OfferManager(self)
            
            self.connecting = False
            self.connected = True
            self.emit("connected")
        
        finally:
            self.connecting = False
    
    def run (self):
        try:
            self._connect()
            while self.isConnected():
                for match, prediction in self.client.read(self.predictions):
                    if not match:
                        connected = False
                        break
                    prediction.callback(match)
        
        except Exception, e:
            if self.connected:
                self.connected = False
            for errortype in (IOError, LogOnError, InterruptError, EOFError,
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

import socket
import re, sys
from sys import maxint

from gobject import *

from telnetlib import Telnet
from pychess.System.Log import log

class VerboseTelnet (Telnet, GObject):
    __gsignals__ = {
        'newString' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,))
    }
    
    def __init__ (self):
        Telnet.__init__(self)
        GObject.__init__(self)
        self.interrupting = False
    
    def expectList (self, regexps):
        d = {}
        for i, regexp in enumerate(regexps):
            compiled = re.compile(regexp)
            d[compiled] = i
        return self.expect(d)
    
    def expect (self, regexps):
        """ Modified expect method, which checks ALL regexps for the one which
        mathces the earliest """
        
        while 1:
            self.process_rawq()
            lowest = []
            for regexp in regexps.iterkeys():
                m = regexp.search(self.cookedq)
                if m:
                    s = m.start()
                    if not lowest or s < lowest[0][1]:
                        lowest = [(m, s, regexps[regexp])]
                    elif s == lowest[0][1]:
                        lowest.append((m, s, regexps[regexp]))
            maxend = 0
            for match, start, val in lowest:
                end = match.end()
                if end > maxend:
                    maxend = end
                yield (val, match.groups())
            self.cookedq = self.cookedq[maxend:]
            if lowest:
                return
            if self.eof:
                break
            self.fill_rawq()
        text = self.read_very_lazy()
        if not text and self.eof:
            raise EOFError
        yield (-1, [])
        
    def process_rawq (self):
        cooked0 = self.cookedq
        Telnet.process_rawq (self)
        cooked1 = self.cookedq
        if len(cooked1) > len(cooked0):
            log.debug (cooked1[len(cooked0):].replace("\r", ""), self.name)
    
    def write (self, data):
        log.log(data, self.name)
        Telnet.write (self, data)
    
    def open(self, host, port):
        self.eof = 0
        self.host = host
        self.port = port
        msg = "getaddrinfo returns an empty list"
        for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                if self.interrupting:
                    self.interrupting = False
                    raise socket.error, "interrupted"
                self.sock = socket.socket(af, socktype, proto)
                self.sock.connect(sa)
            except socket.error, msg:
                if self.sock:
                    self.sock.close()
                self.sock = None
                continue
            break
        if not self.sock:
            raise socket.error, msg
        
        self.name = "%s#%s" % (host, port)
    
    def interrupt (self):
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except socket.error:
                pass
        else:
            self.interrupting = True

from pychess.Utils.const import IC_CONNECTED, IC_DISCONNECTED

client = None
connected = False
connecting = False
registered = False
curname = None

class LogOnError (Exception): pass
class InterruptError (Exception): pass

def connect (host, port, username="guest", password=""):
    
    global client, connected, connecting, registered, curname
    
    connecting = True
    
    try:
        client = VerboseTelnet()
        
        try:
            client.open(host, port)
        except socket.gaierror, e:
            raise IOError, e.args[1]
        except EOFError:
            raise IOError, _("The connection was broken - got \"end of file\" message")
        except socket.error, e:
            raise InterruptError, ", ".join(map(str,e.args))
        except Exception, e:
            raise IOError, str(e)
        
        client.read_until("login: ")
        print >> client, username
        
        if username != "guest":
            r = client.expectList( ["password: ", "login: ",
                    "Press return to enter the server as"]).next()
            if r[0] < 0:
                raise IOError, _("The connection was broken - got \"end of file\" message")
            elif r[0] == 1:
                raise LogOnError, _("Names can only consist of lower and upper case letters")
            elif r[0] == 2:
                raise LogOnError, _("'%s' is not a registered name") % username
            else:
                print >> client, password
                registered = True
        else:
            client.read_until("Press return")
            print >> client
        
        names = "(\w+)(?:\(([CUHIFWM])\))?"
        r = client.expectList( ["Invalid password",
                "Starting FICS session as %s" %  names]).next()
        
        if r[0] == 0:
            raise LogOnError, _("The entered password was invalid.\n\n"+\
                                "If you have forgot your password, try logging in as a guest and open chat on channel 4. Write \"I've forgotten my password\" to get help.\n\n"+\
                                "If that is by some reason not possible, please email: support@freechess.org")
        elif r[0] == 1:
            curname = r[1][0]
        
        client.read_until("fics%")
        
        connected = True
        for handler in connectHandlers:
            handler (client, IC_CONNECTED)
        
        EOF = False
        while connected:
            for match in client.expect(regexps):
                if r[0] < 0:
                    EOF = True
                    break
                funcs, groups = match
                try:
                    for func in funcs:
                        func(client, groups)
                except TypeError:
                    print funcs
                    raise
        
        for handler in connectHandlers:
            # Give handlers a chance no discover that the connection is closed
            handler (client, IC_DISCONNECTED)
    
    except Exception, e:
        connected = False
        connecting = False
        client = None
        raise

def disconnect ():
    global connected
    connected = False

regexps = {}
def expect (regexp, func, flag=None):
    if flag != None:
        r = re.compile(regexp, flag)
    else: r = re.compile(regexp)
    
    if r in regexps:
        regexps[r].append(func)
    else:
        regexps[r] = [func]

def unexpect (func):
    for regexp, funcs in regexps.items():
        try:
            index = funcs.index(func)
            if len(funcs) <= 1:
                del regexps[regexp]
            else:
                del funcs[index]
        except ValueError:
            pass

connectHandlers = []
def connectStatus (func):
    connectHandlers.append(func)

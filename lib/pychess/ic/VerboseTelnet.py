import socket, re
from telnetlib import Telnet

from pychess.System.Log import log

class InterruptError (StandardError): pass

class VerboseTelnet (Telnet):
    
    def __init__ (self):
        Telnet.__init__(self)
        self.connected = False
    
    def expectList (self, regexps):
        d = {}
        for i, regexp in enumerate(regexps):
            compiled = re.compile(regexp)
            d[compiled] = i
        return self.expect(d)
    
    def expect (self, regexps):
        """ Modified expect method, which checks ALL regexps for the one which
        mathces the earliest """
        
        while True:
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
            if self.eof or not self.connected:
                break
            self.fill_rawq()
        text = self.read_very_lazy()
        if not text and self.eof:
            raise EOFError
        yield (-1, [])
    
    def read_until (self, match, timeout=None):
        if self.connected:
            return Telnet.read_until (self, match, timeout)
    
    def process_rawq (self):
        cooked0 = self.cookedq
        Telnet.process_rawq (self)
        cooked1 = self.cookedq
        if len(cooked1) > len(cooked0):
            log.debug (cooked1[len(cooked0):].replace("\r", ""), self.name)
    
    def write (self, data):
        if self.connected:
            log.log(data, self.name)
            Telnet.write (self, data)
        else:
            log.warn("Data not written due to closed telnetclient: '%s'"
                    % data, self.name)
    
    def open(self, host, port):
        self.eof = 0
        self.host = host
        self.port = port
        msg = "getaddrinfo returns an empty list"
        for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
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
        self.connected = True
    
    def close (self):
        self.connected = False
        Telnet.close(self)

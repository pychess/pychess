import socket, re
from copy import copy
from telnetlib import Telnet

from pychess.System.Log import log

READ_LINE, READ_LINE_PLUS, READ_FROMTO = range(3)
class Prediction:
    def __init__ (self, type, callback, regexp0, regexp1=None):
        self.type = type
        self.callback = callback
        
        if type == READ_LINE_PLUS:
            regexp1 = r"[^\\].*"
        
        if not regexp1:
            self.hash = hash(regexp0) + self.type
        else: self.hash = hash(regexp0 + regexp1) + self.type
        
        if not hasattr("match", regexp0):
            regexp0 = re.compile(regexp0)
        if regexp1 and not hasattr("match", regexp1):
            regexp1 = re.compile(regexp1)
        
        self.regexp0 = regexp0
        self.regexp1 = regexp1
    
    def __hash__ (self):
        return self.hash
    
    def __cmp__ (self, other):
        return self.type == other.type and \
               self.regexp0 == other.regexp0 and \
               self.regexp1 == other.regexp1
    
    def __repr__ (self):
        return "<Prediction to %s>" % self.callback

class InterruptError (StandardError): pass

class VerboseTelnet (Telnet):
    
    def __init__ (self):
        Telnet.__init__(self)
        self.connected = False
        self.inbetweens = {}
        self.buffer = ""
    
    def read (self, predictions):
        while True:
            # The prediations list may be changed at any time, so to avoid
            # "changed size during iteration" errors, we make a shallow copy
            temppreds = copy(predictions)
            
            line = self.readline().strip()
            if line.startswith("fics% "):
                line = line[6:]
            amatch = False
            
            if self.inbetweens:
                for prediction in self.inbetweens.keys():
                    match = prediction.regexp1.match(line)
                    if match:
                        #print "GOOUT", repr(line), self.inbetweens[prediction]
                        amatch = True
                        linelist = self.inbetweens[prediction]
                        linelist.append(match)
                        del self.inbetweens[prediction]
                        yield linelist, prediction
            
            else:
                for prediction in temppreds:
                    if prediction in self.inbetweens:
                        continue
                    match = prediction.regexp0.match(line)
                    if match:
                        amatch = True
                        if prediction.type == READ_FROMTO:
                            #print "GOIN", repr(line)
                            self.inbetweens[prediction] = [match]
                        else:
                            yield match, prediction
            
            if not amatch and self.inbetweens:
                for linelist in self.inbetweens.values():
                    linelist.append(line)
            
            if self.eof or not self.connected:
                break
        
        text = self.read_very_lazy()
        if not text and self.eof:
            raise EOFError
        yield (None, None)
    
    def readline (self):
        while True:
            s = self.buffer.split("\n", 1)
            if len(s) == 2:
                self.buffer = s[1]
                return s[0]
            self.buffer += self.read_some()
    
    def process_rawq (self):
        cooked0 = self.cookedq
        Telnet.process_rawq (self)
        cooked1 = self.cookedq
        if len(cooked1) > len(cooked0):
            d = cooked1[len(cooked0):].replace("\r","")
            lines = d.split("\n")
            for line in lines[:-1]:
                log.debug (line+"\n", self.name)
            log.debug(lines[-1], self.name)
    
    def write (self, data):
        if self.connected:
            log.log(data, self.name)
            Telnet.write (self, data)
        else:
            log.warn("Data not written due to closed telnetclient: '%s'"
                    % data, self.name)
    
    def open(self, host, port):
        Telnet.open(self, host, port)
        self.name = "%s#%s" % (self.host, self.port)
        self.connected = True
    
    def close (self):
        self.connected = False
        Telnet.close(self)
























    def expect2 (self, regexps):
        """ Modified expect method, which checks ALL regexps for the one which
        mathces the earliest """
        
        while True:
            self.process_rawq()
            lowest = []
            for regexp in regexps.iterkeys():
                m = regexp.search(self.cookedq)
                if m:
                    s = m.start()
                    if not lowest or s < lowest[0][0]:
                        lowest = [(s, m, regexps[regexp])]
                    elif s == lowest[0][0]:
                        lowest.append((s, m, regexps[regexp]))
            
            for start, match, val in lowest:
                if "Lobais" in match.group() or "Qh4#" in match.group():
                    print match.groups()
                    print val
                yield (val, match.groups())
            
            if lowest:
                self.cookedq = self.cookedq[lowest[0][0]+1:]
                return
            
            if self.eof or not self.connected:
                break
            self.fill_rawq()
        
        text = self.read_very_lazy()
        if not text and self.eof:
            raise EOFError
        yield (None, [])

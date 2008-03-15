import socket
import re, sre_constants
from copy import copy
from telnetlib import Telnet

from pychess.System.Log import log
import timeseal

class Prediction:
    def __init__ (self, callback, regexp0, regexp1=None):
        self.callback = callback
        
        if not regexp1:
            self.hash = hash(regexp0) ^ hash(callback)
        else: self.hash = hash(regexp0) ^ hash(regexp1) ^ hash(callback)
        
        if not hasattr("match", regexp0):
            # FICS being fairly case insensitive, we can compile with IGNORECASE
            # to easy some expressions
            regexp0 = re.compile(regexp0, re.IGNORECASE)
        if regexp1 and not hasattr("match", regexp1):
            regexp1 = re.compile(regexp1, re.IGNORECASE)
        
        self.regexp0 = regexp0
        self.regexp1 = regexp1
    
    def __hash__ (self):
        return self.hash
    
    def __cmp__ (self, other):
        return self.type == other.type and \
               self.regexp0 == other.regexp0 and \
               self.regexp1 == other.regexp1
    
    def __repr__ (self):
        return "<Prediction to %s>" % self.callback.__name__

RETURN_NO_MATCH, RETURN_MATCH, RETURN_NEED_MORE = range(3)

class LinePrediction (Prediction):
    def __init__ (self, callback, regexp0):
        Prediction.__init__(self, callback, regexp0)
    
    def handle(self, line):
        match = self.regexp0.match(line)
        if match:
            self.callback(match)
            return RETURN_MATCH
        return RETURN_NO_MATCH

class ManyLinesPrediction (Prediction):
    def __init__ (self, callback, regexp0):
        Prediction.__init__(self, callback, regexp0)
        self.matchlist = []
    
    def handle(self, line):
        match = self.regexp0.match(line)
        if match:
            self.matchlist.append(match)
            return RETURN_NEED_MORE
        if self.matchlist:
            self.callback(self.matchlist)
        return RETURN_NO_MATCH

class FromPlusPrediction (Prediction):
    def __init__ (self, callback, regexp0, regexp1):
        Prediction.__init__(self, callback, regexp0, regexp1)
        self.matchlist = []
    
    def handle (self, line):
        if not self.matchlist:
            match = self.regexp0.match(line)
            if match:
                self.matchlist.append(match)
                return RETURN_NEED_MORE
        else:
            match = self.regexp1.match(line)
            if match:
                self.matchlist.append(match)
                return RETURN_NEED_MORE
            else:
                self.callback(self.matchlist)
                del self.matchlist[:]
                return RETURN_NO_MATCH
        return RETURN_NO_MATCH

class FromToPrediction (Prediction):
    def __init__ (self, callback, regexp0, regexp1):
        Prediction.__init__(self, callback, regexp0, regexp1)
        self.matchlist = []
    
    def handle (self, line):
        if not self.matchlist:
            match = self.regexp0.match(line)
            if match:
                self.matchlist.append(match)
                return RETURN_NEED_MORE
        else:
            match = self.regexp1.match(line)
            if match:
                self.matchlist.append(match)
                self.callback(self.matchlist)
                del self.matchlist[:]
                return RETURN_MATCH
            else:
                self.matchlist.append(line)
                return RETURN_NEED_MORE
        return RETURN_NO_MATCH

class VerboseTelnet (Telnet):
    
    def __init__ (self):
        Telnet.__init__(self)
        self.connected = False
        self.state = None
        self.buffer = ""
    
    def handleSomeText (self, predictions):
        # The prediations list may be changed at any time, so to avoid
        # "changed size during iteration" errors, we make a shallow copy
        temppreds = copy(predictions)
        
        line = self.readline().strip()
        if line.startswith("fics% "):
            line = line[6:]
        elif line == "fics%":
            line = ""
        
        if self.state:
            answer = self.state.handle(line)
            if answer != RETURN_NEED_MORE:
                self.state = None
            if answer != RETURN_NO_MATCH:
                return
        #print "line", line
        if not self.state:
            for prediction in temppreds:
                answer = prediction.handle(line)
                if answer == RETURN_NEED_MORE:
                    self.state = prediction
                if answer != RETURN_NO_MATCH:
                    break
            else:
                log.debug(line+"\n", "nonmatched")
    
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

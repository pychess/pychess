import socket
import re, sre_constants
from copy import copy
from telnetlib import Telnet

from pychess.System.Log import log

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
        self.old = regexp0
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

class VerboseTelnet:
    def __init__ (self, telnet):
        self.telnet = telnet
    
    def open (self, address, port):
        return self.telnet.open(address, port)
    
    def read_until (self, *untils):
        return self.telnet.read_until(*untils)
    
    def readline (self):
        line = self.telnet.readline()
        #log.debug(line, repr(self.telnet))
        return line
    
    def write(self, str):
        log.log(str, repr(self.telnet))
        self.telnet.write(str)
    
    def close (self):
        self.telnet.close()

class PredictionsTelnet:
    def __init__ (self, telnet):
        self.telnet = telnet
        self.__state = None
        
        self.__stripLines = True
        self.__linePrefix = None
    
    def getStripLines(self):
        return self.__stripLines
    def getLinePrefix(self):
        return self.__linePrefix
    def setStripLines(self, value):
        self.__stripLines = value
    def setLinePrefix(self, value):
        self.__linePrefix = value

    def handleSomeText (self, predictions):
        # The prediations list may be changed at any time, so to avoid
        # "changed size during iteration" errors, we make a shallow copy
        temppreds = copy(predictions)
        
        line = self.telnet.readline()
        line = line.lstrip()
        
        if self.getLinePrefix() and self.getLinePrefix() in line:
            while line.startswith(self.getLinePrefix()):
                line = line[len(self.getLinePrefix()):]
                if self.getStripLines():
                    line = line.lstrip()
        
        origLine = line
        if self.getStripLines():
            line = line.strip()
        
        if self.__state:
            answer = self.__state.handle(line)
            if answer in (RETURN_NO_MATCH, RETURN_MATCH):
                self.__state = None
            if answer in (RETURN_MATCH, RETURN_NEED_MORE):
                return
        
        if not self.__state:
            for prediction in temppreds:
                answer = prediction.handle(line)
                if answer == RETURN_NEED_MORE:
                    self.__state = prediction
                if answer in (RETURN_MATCH, RETURN_NEED_MORE):
                    break
            else:
                log.debug(origLine, "nonmatched")
    
    def write(self, str):
        return self.telnet.write(str)
    
    def close (self):
        self.telnet.close()

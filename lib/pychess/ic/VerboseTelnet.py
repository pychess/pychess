import socket
import re, sre_constants
from copy import copy

from pychess.System.Log import log

class Prediction:
    def __init__ (self, callback, *regexps):
        self.callback = callback
        
        self.regexps = []
        self.hash = hash(callback)
        for regexp in regexps:
            self.hash ^= hash(regexp)
            
            if not hasattr("match", regexp):
                # FICS being fairly case insensitive, we can compile with IGNORECASE
                # to easy some expressions
                self.regexps.append(re.compile(regexp, re.IGNORECASE))
    
    def __hash__ (self):
        return self.hash
    
    def __cmp__ (self, other):
        return self.callback == other.callback and \
               self.regexps == other.regexps
    
    def __repr__ (self):
        return "<Prediction to %s>" % self.callback.__name__

RETURN_NO_MATCH, RETURN_MATCH, RETURN_NEED_MORE = range(3)

class LinePrediction (Prediction):
    def __init__ (self, callback, regexp):
        Prediction.__init__(self, callback, regexp)
    
    def handle(self, line):
        match = self.regexps[0].match(line)
        if match:
            self.callback(match)
            return RETURN_MATCH
        return RETURN_NO_MATCH

class ManyLinesPrediction (Prediction):
    def __init__ (self, callback, regexp):
        Prediction.__init__(self, callback, regexp)
        self.matchlist = []
    
    def handle(self, line):
        match = self.regexps[0].match(line)
        if match:
            self.matchlist.append(match)
            return RETURN_NEED_MORE
        if self.matchlist:
            self.callback(self.matchlist)
        return RETURN_NO_MATCH

class NLinesPrediction (Prediction):
    def __init__ (self, callback, *regexps):
        Prediction.__init__(self, callback, *regexps)
        self.matchlist = []
    
    def handle(self, line):
        regexp = self.regexps[len(self.matchlist)]
        match = regexp.match(line)
        if match:
            self.matchlist.append(match)
            if len(self.matchlist) == len(self.regexps):
                self.callback(self.matchlist)
                del self.matchlist[:]
                return RETURN_MATCH
            return RETURN_NEED_MORE
        return RETURN_NO_MATCH

class FromPlusPrediction (Prediction):
    def __init__ (self, callback, regexp0, regexp1):
        Prediction.__init__(self, callback, regexp0, regexp1)
        self.matchlist = []
    
    def handle (self, line):
        if not self.matchlist:
            match = self.regexps[0].match(line)
            if match:
                self.matchlist.append(match)
                return RETURN_NEED_MORE
        else:
            match = self.regexps[1].match(line)
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
            match = self.regexps[0].match(line)
            if match:
                self.matchlist.append(match)
                return RETURN_NEED_MORE
        else:
            match = self.regexps[1].match(line)
            if match:
                self.matchlist.append(match)
                self.callback(self.matchlist)
                del self.matchlist[:]
                return RETURN_MATCH
            else:
                self.matchlist.append(line)
                return RETURN_NEED_MORE
        return RETURN_NO_MATCH

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
            log.debug(line+"\n", (repr(self.telnet), "lines"))
        
        if self.__state:
            answer = self.__state.handle(line)
            if answer != RETURN_NO_MATCH:
                log.debug(line+"\n", (repr(self.telnet), repr(self.__state.callback.__name__)))
            if answer in (RETURN_NO_MATCH, RETURN_MATCH):
                self.__state = None
            if answer in (RETURN_MATCH, RETURN_NEED_MORE):
                return
        
        if not self.__state:
            for prediction in temppreds:
                answer = prediction.handle(line)
                if answer != RETURN_NO_MATCH:
                    log.debug(line+"\n", (repr(self.telnet), repr(prediction.callback.__name__)))
                if answer == RETURN_NEED_MORE:
                    self.__state = prediction
                if answer in (RETURN_MATCH, RETURN_NEED_MORE):
                    break
            else:
                log.debug(origLine, (repr(self.telnet), "nonmatched"))
    
    def write(self, str):
        return self.telnet.write(str)
    
    def close (self):
        self.telnet.close()

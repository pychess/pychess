import collections
import re

from pychess.System.Log import log
from pychess.ic.block_codes import BLOCK_START, BLOCK_SEPARATOR, BLOCK_END


class ConsoleHandler():
    def __init__ (self, callback):
        self.callback = callback
    
    def handle(self, line, block_code=None):
        if line:
            self.callback(line, block_code)

class Prediction:
    def __init__ (self, callback, *regexps):
        self.callback = callback
        self.name = callback.__name__
        self.regexps = []
        self.matches = ()
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


RETURN_NO_MATCH, RETURN_MATCH, RETURN_NEED_MORE, RETURN_MATCH_END = range(4)

class LinePrediction (Prediction):
    def __init__ (self, callback, regexp):
        Prediction.__init__(self, callback, regexp)
    
    def handle(self, line):
        match = self.regexps[0].match(line)
        if match:
            self.matches = (match.string,)
            self.callback(match)
            return RETURN_MATCH
        return RETURN_NO_MATCH

class MultipleLinesPrediction (Prediction):
    def __init__ (self, callback, *regexps):
        Prediction.__init__(self, callback, *regexps)
        self.matchlist = []

class NLinesPrediction (MultipleLinesPrediction):
    def __init__ (self, callback, *regexps):
        MultipleLinesPrediction.__init__(self, callback, *regexps)
    
    def handle(self, line):
        regexp = self.regexps[len(self.matchlist)]
        match = regexp.match(line)
        if match:
            self.matchlist.append(match)
            if len(self.matchlist) == len(self.regexps):
                self.matches = [m.string for m in self.matchlist]
                self.callback(self.matchlist)
                del self.matchlist[:]
                return RETURN_MATCH
            return RETURN_NEED_MORE
        return RETURN_NO_MATCH

class FromPlusPrediction (MultipleLinesPrediction):
    def __init__ (self, callback, regexp0, regexp1):
        MultipleLinesPrediction.__init__(self, callback, regexp0, regexp1)
    
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
                self.matches = [m.string for m in self.matchlist]
                self.callback(self.matchlist)
                del self.matchlist[:]
                return RETURN_MATCH_END
        return RETURN_NO_MATCH

class FromToPrediction (MultipleLinesPrediction):
    def __init__ (self, callback, regexp0, regexp1):
        MultipleLinesPrediction.__init__(self, callback, regexp0, regexp1)
    
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
                self.matches = [m if type(m) is str else m.string for m in self.matchlist]
                self.callback(self.matchlist)
                del self.matchlist[:]
                return RETURN_MATCH
            else:
                self.matchlist.append(line)
                return RETURN_NEED_MORE
        return RETURN_NO_MATCH

class PredictionsTelnet:
    def __init__ (self, telnet, predictions, reply_cmd_dict):
        self.telnet = telnet
        self.predictions = predictions
        self.reply_cmd_dict = reply_cmd_dict
        self.lines = collections.deque()
        self.consolehandler = None
        self.__linePrefix = None
        self.__block_mode = False
        self.__command_id = 0
        self._inReply = False
    
    def getLinePrefix(self):
        return self.__linePrefix

    def setLinePrefix(self, value):
        self.__linePrefix = value

    def setBlockModeOn(self):
        self.__block_mode = True
    
    def get_line (self):
        block_code = None
        try:
            line, block_code = self.lines.popleft()
        except IndexError:
            line = self.telnet.readline().strip()
        
        if line.startswith(self.getLinePrefix()):
            line = line[len(self.getLinePrefix())+1:]
        
        if self.__block_mode and line.startswith(BLOCK_START):
            line, block_code = self.parse_cmd_reply(line)
            
        log.debug(line+"\n", (self.telnet.name, "lines"))
        if self.consolehandler is not None:
            self.consolehandler.handle(line, block_code)
        
        return line, block_code
    
    def parse_cmd_reply (self, line):
        parts = line[1:].split(BLOCK_SEPARATOR)
        if len(parts) == 3:
            id, code, text = parts
        elif len(parts) == 4:
            id, code, error_code, text = parts
        else:
            log.warn("Posing not supported yet\n", (self.telnet.name, "lines"))
            return
        code = int(code)
        line = text if text else self.telnet.readline().strip()
        
        while not line.endswith(BLOCK_END):
            self.lines.append((line, code))
            line = self.telnet.readline().strip()
        self.lines.append((line[:-1], code))
        
        log.debug("%s %s %s\n" %
                  (id, code, "\n".join(line[0] for line in self.lines)),
                  (self.telnet.name, "command_reply"))
        return self.lines.popleft()
    
    def parse_line(self, line):
        line, code = line
        if not line: return # TODO: necessary?
        
        for p in (reversed(self.reply_cmd_dict[code]) if code and code in \
                self.reply_cmd_dict else self.predictions):
#            print "parse_line: trying prediction %s for line '%s'" % (p.name, line)
            answer = self.test_prediction(p, line, code)
            if answer in (RETURN_MATCH, RETURN_MATCH_END):
                log.debug("\n".join(p.matches)+"\n", (self.telnet.name, p.name))
                break
        else:
            log.debug(line+"\n", (self.telnet.name, "nonmatched"))
    
    def test_prediction (self, prediction, line, code):
        lines = []
        answer = prediction.handle(line)        
        while answer is RETURN_NEED_MORE:
            line, code = self.get_line()
            lines.append(line)
            answer = prediction.handle(line)
        
        if lines and answer not in (RETURN_MATCH, RETURN_MATCH_END):
            for line in reversed(lines):
                self.lines.appendleft((line, code))
        elif answer is RETURN_MATCH_END:
            self.lines.appendleft((line, code)) # re-test last line that didn't match
            
        return answer
        
    def run_command(self, text):
        if self.__block_mode:
            # TODO: reuse id after command reply handled
            self.__command_id += 1
            text = "%s %s\n" % (self.__command_id, text)
            return self.telnet.write(text)
        else:
            return self.telnet.write("%s\n" % text)
    
    def close (self):
        self.telnet.close()

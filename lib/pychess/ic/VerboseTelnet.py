import collections
import re

from pychess.System.Log import log
from pychess.ic import BLOCK_START, BLOCK_SEPARATOR, BLOCK_END

class ConsoleHandler (object):
    def __init__ (self, callback):
        self.callback = callback
    
    def handle(self, line):
        if line:
            self.callback(line)

class Prediction (object):
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
        del self.matchlist[:]
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
        del self.matchlist[:]
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

TelnetLine = collections.namedtuple('TelnetLine', ['line', 'code'])

class TelnetLines (object):
    def __init__ (self, telnet):
        self.telnet = telnet
        self.lines = collections.deque()
        self._block_mode = False
        self._line_prefix = None
        self.consolehandler = None
        
    @property
    def block_mode (self):
        return self._block_mode
    @block_mode.setter
    def block_mode (self, x):
        self._block_mode = x

    @property
    def line_prefix (self):
        return self._line_prefix
    @line_prefix.setter
    def line_prefix (self, x):
        self._line_prefix = x
    
    def appendleft (self, x):
        self.lines.appendleft(x)
    
    def extendleft (self, iterable):
        self.lines.extendleft(iterable)
    
    def popleft (self):
        try:
            return self.lines.popleft()
        except IndexError:
            self.lines.extend(self._get_lines())
            return self.lines.popleft()
        
    def _get_lines (self):
        lines = []
        line = self.telnet.readline().strip()
        
        if line.startswith(self.line_prefix):
            line = line[len(self.line_prefix)+1:]
        
        if self.block_mode and line.startswith(BLOCK_START):
            parts = line[1:].split(BLOCK_SEPARATOR)
            if len(parts) == 3:
                id, code, text = parts
            elif len(parts) == 4:
                id, code, error_code, text = parts
            else:
                log.warning("Posing not supported yet",
                            extra={"task": (self.telnet.name, "lines")})
                return lines
            code = int(code)
            line = text if text else self.telnet.readline().strip()
            
            while not line.endswith(BLOCK_END):
                lines.append(TelnetLine(line, code))
                line = self.telnet.readline().strip()
            lines.append(TelnetLine(line[:-1], code))
            
            log.debug("%s %s %s" %
                      (id, code, "\n".join(line.line for line in lines).strip()),
                      extra={"task": (self.telnet.name, "command_reply")})
        else:
            lines.append(TelnetLine(line, None))

        log.debug("\n".join(line.line for line in lines).strip(),
                  extra={"task": (self.telnet.name, "lines")})
        if self.consolehandler:
            self.consolehandler.handle(lines)
        
        return lines
    
class PredictionsTelnet (object):
    def __init__ (self, telnet, predictions, reply_cmd_dict):
        self.telnet = telnet
        self.predictions = predictions
        self.reply_cmd_dict = reply_cmd_dict
        self.lines = TelnetLines(telnet)
        self.__command_id = 0
    
    def parse (self):
        line = self.lines.popleft()
        if not line.line: return # TODO: necessary?
        
        for p in (reversed(self.reply_cmd_dict[line.code])
                  if line.code and line.code in self.reply_cmd_dict
                  else self.predictions):
#            print "parse_line: trying prediction %s for line '%s'" % (p.name, line)
            answer = self.test_prediction(p, line)
            if answer in (RETURN_MATCH, RETURN_MATCH_END):
                log.debug("\n".join(p.matches), extra={"task": (self.telnet.name, p.name)})
                break
        else:
            log.debug(line.line, extra={"task": (self.telnet.name, "nonmatched")})
    
    def test_prediction (self, prediction, line):
        lines = []
        answer = prediction.handle(line.line)        
        while answer is RETURN_NEED_MORE:
            line = self.lines.popleft()
            lines.append(line)
            answer = prediction.handle(line.line)
        
        if lines and answer not in (RETURN_MATCH, RETURN_MATCH_END):
            self.lines.extendleft(reversed(lines))
        elif answer is RETURN_MATCH_END:
            self.lines.appendleft(line) # re-test last line that didn't match
            
        return answer
        
    def run_command(self, text):
        log.debug(text, extra={"task": (self.telnet.name, "run_command")})
        if self.lines.block_mode:
            # TODO: reuse id after command reply handled
            self.__command_id += 1
            text = "%s %s\n" % (self.__command_id, text)
            return self.telnet.write(text)
        else:
            return self.telnet.write("%s\n" % text)

    def cancel (self):
        self.run_command("quit")
        self.telnet.cancel()
    
    def close (self):
        self.run_command("quit")
        self.telnet.close()

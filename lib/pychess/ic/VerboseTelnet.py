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
                #print "FromToPrediction %s (to) match: %s" % (self.name, line)
                self.matchlist.append(match)
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

        self.consolehandler = None
      
        self.__state = None
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

    def handleSomeText (self):
        line = self.telnet.readline().strip()
        if self.__block_mode and self._inReply:
            id, code, text = self._inReply
            if line.endswith(BLOCK_END):
                self._inReply = None
                line = line[:-1]
                self.handle_command_reply(id, code, "%s\n%s" % (text, line))
            else:
                self._inReply = (id, code, "%s\n%s" % (text, line))
            return
        
        if line.startswith(self.getLinePrefix()):
            line = line[len(self.getLinePrefix())+1:]

        if self.__block_mode:
            if line.startswith(BLOCK_START):
                line = line[1:]
                parts = line.split(BLOCK_SEPARATOR)
                if len(parts) == 3:
                    id, code, text = parts
                elif len(parts) == 4:
                    id, code, error_code, text = parts
                else:
                    print "Posing not supported yet..."
                    return
                line = text
                if text.endswith(BLOCK_END):
                    line = text[:-1]
                    self.handle_command_reply(id, code, line)
                else:
                    self._inReply = (id, code, line)
                return
        
        self.parseNormalLine(line)

    def parseNormalLine(self, line, block_code=None):
        log.debug(line+"\n", (self.telnet.name, "lines"))
        origLine = line

        if self.__state:
            prediction = self.__state
            answer = self.__state.handle(line)
            if answer != RETURN_NO_MATCH:
                log.debug(line+"\n", (self.telnet.name, prediction.name))
            if answer in (RETURN_NO_MATCH, RETURN_MATCH):
                self.__state = None
            if answer in (RETURN_MATCH, RETURN_NEED_MORE):
                if self.consolehandler is not None:
                    self.consolehandler.handle(line, block_code)
                return
        
        if not self.__state:
            preds = (self.reply_cmd_dict[block_code],) if block_code in self.reply_cmd_dict else self.predictions
            for prediction in preds:
                answer = prediction.handle(line)
                if answer != RETURN_NO_MATCH:
                    log.debug(line+"\n", (self.telnet.name, prediction.name))
                if answer == RETURN_NEED_MORE:
                    self.__state = prediction
                if answer in (RETURN_MATCH, RETURN_NEED_MORE):
                    if self.consolehandler is not None:
                        self.consolehandler.handle(line, block_code)
                    break
            else:
                if self.consolehandler is not None:
                    self.consolehandler.handle(line)
                log.debug(origLine+"\n", (self.telnet.name, "nonmatched"))
    
    def run_command(self, text):
        if self.__block_mode:
            # TODO: reuse id after command reply hadled
            self.__command_id += 1
            text = "%s %s\n" % (self.__command_id, text)
            return self.telnet.write(text)
        else:
            return self.telnet.write("%s\n" % text)

    def handle_command_reply(self, id, code, text):
        for line in text.splitlines():
            self.parseNormalLine(line, int(code))
        log.debug("%s %s %s" % (id, code, text) + "\n", (self.telnet.name, "command_reply"))
    
    def close (self):
        self.telnet.close()

import collections
import re

from pychess.System.Log import log
from pychess.ic import BLOCK_START, BLOCK_SEPARATOR, BLOCK_END, BLKCMD_PASSWORD


class ConsoleHandler(object):
    def __init__(self, callback):
        self.callback = callback

    def handle(self, line):
        if line:
            self.callback(line)


class Prediction(object):
    def __init__(self, callback, *regexps):
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

    def __hash__(self):
        return self.hash

    def __len__(self):
        return len(self.regexps)


RETURN_NO_MATCH, RETURN_MATCH, RETURN_NEED_MORE, RETURN_MATCH_END = range(4)


class LinePrediction(Prediction):
    def __init__(self, callback, regexp):
        Prediction.__init__(self, callback, regexp)

    def handle(self, line):
        match = self.regexps[0].match(line)
        if match:
            self.matches = (match.string, )
            self.callback(match)
            return RETURN_MATCH
        return RETURN_NO_MATCH


class MultipleLinesPrediction(Prediction):
    def __init__(self, callback, *regexps):
        Prediction.__init__(self, callback, *regexps)
        self.matchlist = []


class NLinesPrediction(MultipleLinesPrediction):
    def __init__(self, callback, *regexps):
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


class FromPlusPrediction(MultipleLinesPrediction):
    def __init__(self, callback, regexp0, regexp1):
        MultipleLinesPrediction.__init__(self, callback, regexp0, regexp1)

    def handle(self, line):
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


class FromABPlusPrediction(MultipleLinesPrediction):
    def __init__(self, callback, regexp0, regexp1, regexp2):
        MultipleLinesPrediction.__init__(self, callback, regexp0, regexp1,
                                         regexp2)

    def handle(self, line):
        if not self.matchlist:
            match = self.regexps[0].match(line)
            if match:
                self.matchlist.append(match)
                return RETURN_NEED_MORE
        elif len(self.matchlist) == 1:
            match = self.regexps[1].match(line)
            if match:
                self.matchlist.append(match)
                return RETURN_NEED_MORE
        else:
            match = self.regexps[2].match(line)
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


class FromToPrediction(MultipleLinesPrediction):
    def __init__(self, callback, regexp0, regexp1):
        MultipleLinesPrediction.__init__(self, callback, regexp0, regexp1)

    def handle(self, line):
        if not self.matchlist:
            match = self.regexps[0].match(line)
            if match:
                self.matchlist.append(match)
                return RETURN_NEED_MORE
        else:
            match = self.regexps[1].match(line)
            if match:
                self.matchlist.append(match)
                self.matches = [m if isinstance(m, str) else m.string
                                for m in self.matchlist]
                self.callback(self.matchlist)
                del self.matchlist[:]
                return RETURN_MATCH
            else:
                self.matchlist.append(line)
                return RETURN_NEED_MORE
        return RETURN_NO_MATCH


TelnetLine = collections.namedtuple('TelnetLine', ['line', 'code'])
EmptyTelnetLine = TelnetLine("", None)


class TelnetLines(object):
    def __init__(self, telnet, show_reply):
        self.telnet = telnet
        self.lines = collections.deque()
        self._block_mode = False
        self._line_prefix = None
        self.consolehandler = None
        self.show_reply = show_reply

    @property
    def block_mode(self):
        return self._block_mode

    @block_mode.setter
    def block_mode(self, x):
        self._block_mode = x

    @property
    def line_prefix(self):
        return self._line_prefix

    @line_prefix.setter
    def line_prefix(self, x):
        self._line_prefix = x

    def appendleft(self, x):
        self.lines.appendleft(x)

    def extendleft(self, iterable):
        self.lines.extendleft(iterable)

    def popleft(self):
        try:
            return self.lines.popleft()
        except IndexError:
            self.lines.extend(self._get_lines())
            return self.lines.popleft() if self.lines else EmptyTelnetLine

    def _get_lines(self):
        lines = []
        line = self.telnet.readline()
        identifier = 0

        if line.startswith(self.line_prefix):
            line = line[len(self.line_prefix) + 1:]

        if self.block_mode and line.startswith(BLOCK_START):
            parts = line[1:].split(BLOCK_SEPARATOR)
            if len(parts) == 3:
                identifier, code, text = parts
            elif len(parts) == 4:
                identifier, code, error_code, text = parts
            else:
                log.warning("Posing not supported yet",
                            extra={"task": (self.telnet.name, "lines")})
                return lines
            code = int(code)
            identifier = int(identifier)
            line = text if text else self.telnet.readline()

            while not line.endswith(BLOCK_END):
                lines.append(TelnetLine(line, code))
                line = self.telnet.readline()
            lines.append(TelnetLine(line[:-1], code))

            if code != BLKCMD_PASSWORD:
                log.debug("%s %s %s" %
                          (identifier, code, "\n".join(line.line
                                                       for line in lines).strip()),
                          extra={"task": (self.telnet.name, "command_reply")})
        else:
            code = 0
            lines.append(TelnetLine(line, None))

        if code != BLKCMD_PASSWORD:
            log.debug("\n".join(line.line for line in lines).strip(),
                      extra={"task": (self.telnet.name, "lines")})
        if self.consolehandler:
            if identifier == 0 or identifier in self.show_reply:
                self.consolehandler.handle(lines)
                # self.show_reply.discard(identifier)

        return lines


class PredictionsTelnet(object):
    def __init__(self, telnet, predictions, reply_cmd_dict):
        self.telnet = telnet
        self.predictions = predictions
        self.reply_cmd_dict = reply_cmd_dict
        self.show_reply = set([])
        self.lines = TelnetLines(telnet, self.show_reply)
        self.__command_id = 1

    def parse(self):
        line = self.lines.popleft()
        if not line.line:
            return  # TODO: necessary?

        predictions = self.reply_cmd_dict[line.code] \
            if line.code and line.code in self.reply_cmd_dict else self.predictions
        for pred in list(predictions):
            #            print "parse_line: trying prediction %s for line '%s'" % (pred.name, line)
            answer = self.test_prediction(pred, line)
            if answer in (RETURN_MATCH, RETURN_MATCH_END):
                log.debug("\n".join(pred.matches),
                          extra={"task": (self.telnet.name, pred.name)})
                break
        else:
            if line.code != BLKCMD_PASSWORD:
                log.debug(line.line,
                          extra={"task": (self.telnet.name, "nonmatched")})

    def test_prediction(self, prediction, line):
        lines = []
        answer = prediction.handle(line.line)
        while answer is RETURN_NEED_MORE:
            line = self.lines.popleft()
            lines.append(line)
            answer = prediction.handle(line.line)

        if lines and answer not in (RETURN_MATCH, RETURN_MATCH_END):
            self.lines.extendleft(reversed(lines))
        elif answer is RETURN_MATCH_END:
            self.lines.appendleft(line)  # re-test last line that didn't match

        return answer

    def run_command(self, text, show_reply=False):
        logtext = "*" * len(text) if self.telnet.sensitive else text
        log.debug(logtext, extra={"task": (self.telnet.name, "run_command")})
        if self.lines.block_mode:
            # TODO: reuse id after command reply handled
            self.__command_id += 1
            text = "%s %s\n" % (self.__command_id, text)
            if show_reply:
                self.show_reply.add(self.__command_id)
            return self.telnet.write(text)
        else:
            return self.telnet.write("%s\n" % text)

    def cancel(self):
        self.run_command("quit")
        self.telnet.cancel()

    def close(self):
        # save played game (if there is any) if no moves made
        self.run_command("abort")
        self.run_command("quit")
        self.telnet.close()

import asyncio
import collections
import re

from pychess.System.Log import log
from pychess.ic import BLOCK_START, BLOCK_SEPARATOR, BLOCK_END, BLKCMD_PASSWORD
from pychess.ic.icc import UNIT_START, UNIT_END, DTGR_START, MY_ICC_PREFIX


class ConsoleHandler:
    def __init__(self, callback):
        self.callback = callback

    def handle(self, line):
        if line:
            self.callback(line)


class Prediction:
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
BL, DG, CN = range(3)


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


TelnetLine = collections.namedtuple('TelnetLine', ['line', 'code', 'code_type'])
EmptyTelnetLine = TelnetLine("", None, None)


class TelnetLines:
    def __init__(self, telnet, show_reply):
        self.telnet = telnet
        self.lines = collections.deque()
        self.block_mode = False
        self.datagram_mode = False
        self.line_prefix = None
        self.consolehandler = None
        self.show_reply = show_reply

    def appendleft(self, x):
        self.lines.appendleft(x)

    def extendleft(self, iterable):
        self.lines.extendleft(iterable)

    @asyncio.coroutine
    def popleft(self):
        try:
            return self.lines.popleft()
        except IndexError:
            lines = yield from self._get_lines()
            self.lines.extend(lines)
            return self.lines.popleft() if self.lines else EmptyTelnetLine

    @asyncio.coroutine
    def _get_lines(self):
        lines = []
        line = yield from self.telnet.readline()
        identifier = 0

        if line.startswith(self.line_prefix):
            line = line[len(self.line_prefix) + 1:]

        if self.datagram_mode:
            identifier = -1
            code = 0
            unit = False
            if line.startswith(UNIT_START):
                unit = True
                unit_lines = []
                cn_code = int(line[2:line.find(" ")])
                if MY_ICC_PREFIX in line:
                    identifier = 0
                line = yield from self.telnet.readline()

            if unit:
                while UNIT_END not in line:
                    if line.startswith(DTGR_START):
                        code, data = line[2:-2].split(" ", 1)
                        log.debug("%s %s" % (code, data), extra={"task": (self.telnet.name, "datagram")})
                        lines.append(TelnetLine(data, int(code), DG))
                    else:
                        if line.endswith(UNIT_END):
                            parts = line.split(UNIT_END)
                            if parts[0]:
                                unit_lines.append(parts[0])
                        else:
                            unit_lines.append(line)
                    line = yield from self.telnet.readline()
                if len(unit_lines) > 0:
                    text = "\n".join(unit_lines)
                    lines.append(TelnetLine(text, cn_code, CN))
                    log.debug(text, extra={"task": (self.telnet.name, "not datagram")})

        elif self.block_mode and line.startswith(BLOCK_START):
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
            if text:
                line = text
            else:
                line = yield from self.telnet.readline()

            while not line.endswith(BLOCK_END):
                lines.append(TelnetLine(line, code, BL))
                line = yield from self.telnet.readline()
            lines.append(TelnetLine(line[:-1], code, BL))

            if code != BLKCMD_PASSWORD:
                log.debug("%s %s %s" %
                          (identifier, code, "\n".join(line.line
                                                       for line in lines).strip()),
                          extra={"task": (self.telnet.name, "command_reply")})
        else:
            code = 0
            lines.append(TelnetLine(line, None, None))

        if self.consolehandler:
            if identifier == 0 or identifier in self.show_reply:
                self.consolehandler.handle(lines)
                # self.show_reply.discard(identifier)

        return lines


class PredictionsTelnet:
    def __init__(self, telnet, predictions, reply_cmd_dict, replay_dg_dict, replay_cn_dict):
        self.telnet = telnet
        self.predictions = predictions
        self.reply_cmd_dict = reply_cmd_dict
        self.replay_dg_dict = replay_dg_dict
        self.replay_cn_dict = replay_cn_dict
        self.show_reply = set([])
        self.lines = TelnetLines(telnet, self.show_reply)
        self.__command_id = 1

    @asyncio.coroutine
    def parse(self):
        line = yield from self.lines.popleft()

        if not line.line:
            return  # TODO: necessary?
        # print("line.line:", line.line)
        if self.lines.datagram_mode and line.code is not None:
            if line.code_type == DG:
                callback = self.replay_dg_dict[line.code]
                callback(line.line)
                log.debug(line.line, extra={"task": (self.telnet.name, callback.__name__)})
                return
            elif line.code_type == CN and line.code in self.replay_cn_dict:
                callback = self.replay_cn_dict[line.code]
                callback(line.line)
                log.debug(line.line, extra={"task": (self.telnet.name, callback.__name__)})
                return

        predictions = self.reply_cmd_dict[line.code] \
            if line.code is not None and line.code in self.reply_cmd_dict else self.predictions
        for pred in list(predictions):
            answer = yield from self.test_prediction(pred, line)
            # print(answer, "  parse_line: trying prediction %s for line '%s'" % (pred.name, line.line[:80]))
            if answer in (RETURN_MATCH, RETURN_MATCH_END):
                log.debug("\n".join(pred.matches),
                          extra={"task": (self.telnet.name, pred.name)})
                break
        else:
            # print("  NOT MATCHED:", line.line[:80])
            if line.code != BLKCMD_PASSWORD:
                log.debug(line.line,
                          extra={"task": (self.telnet.name, "nonmatched")})

    @asyncio.coroutine
    def test_prediction(self, prediction, line):
        lines = []
        answer = prediction.handle(line.line)
        while answer is RETURN_NEED_MORE:
            line = yield from self.lines.popleft()
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
            text = "%s %s" % (self.__command_id, text)
            if show_reply:
                self.show_reply.add(self.__command_id)
            self.telnet.write(text)
        elif self.lines.datagram_mode:
            if show_reply:
                text = "`%s`%s" % (MY_ICC_PREFIX, text)
            self.telnet.write("%s" % text)
        else:
            self.telnet.write("%s" % text)

    def cancel(self):
        self.run_command("quit")
        self.telnet.cancel()

    def close(self):
        # save played game (if there is any) if no moves made
        self.run_command("abort")
        self.run_command("quit")
        self.telnet.close()

from __future__ import print_function

import asyncio
import sys
import telnetlib
import random
import time
import platform
import subprocess
import getpass
import os

from pychess.System.Log import log
from pychess.System import searchPath
from pychess.System.prefix import getEngineDataPrefix
from pychess.ic.icc import B_DTGR_END, B_UNIT_END


ENCODE = [ord(i) for i in "Timestamp (FICS) v1.0 - programmed by Henrik Gram."]
ENCODELEN = len(ENCODE)
G_RESPONSE = "\x029"
FILLER = b"1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
IAC_WONT_ECHO = b''.join([telnetlib.IAC, telnetlib.WONT, telnetlib.ECHO])


class CanceledException(Exception):
    pass


class ICSTelnetProtocol(asyncio.Protocol):
    def __init__(self, telnet):
        self.telnet = telnet

    def data_received(self, data):
        self.telnet.cook_some(data)


class ICSTelnet():
    sensitive = False

    def __init__(self):
        self.name = ""
        self.connected = False
        self.canceled = False
        self.FatICS = False
        self.USCN = False
        self.ICC = False
        self.buf = bytearray(b"")
        self.stateinfo = None
        self.timeseal = False

    @asyncio.coroutine
    def start(self, host, port, connected_event, timeseal=True):
        if self.canceled:
            raise CanceledException()

        self.port = port
        self.host = host
        self.connected_event = connected_event
        self.timeseal = timeseal

        self.name = host

        if host == "chessclub.com":
            self.ICC = True
            self.timeseal = False

            # You can get ICC timestamp from
            # https://www.chessclub.com/user/resources/icc/timestamp/
            if sys.platform == "win32":
                timestamp = "timestamp_win32.exe"
            else:
                timestamp = "timestamp_linux_2.6.8"

            altpath = os.path.join(getEngineDataPrefix(), timestamp)
            path = searchPath(timestamp, os.X_OK, altpath=altpath)
            if path:
                self.host = "localhost"
                self.port = 5500
                try:
                    self.timestamp_proc = subprocess.Popen(["%s" % path, "-p", "%s" % self.port])
                    log.info("%s started OK" % path)
                except OSError as err:
                    log.info("Can't start %s OSError: %s %s" % (err.errno, err.strerror, path))
                    self.port = port
                    self.host = host
            else:
                log.info("%s not found" % altpath)

        loop = asyncio.get_event_loop()
        coro = loop.create_connection(lambda: ICSTelnetProtocol(self), self.host, self.port)
        self.transport, self.protocol = yield from coro
        if self.timeseal:
            self.write(self.get_init_string())

    def cancel(self):
        self.canceled = True
        self.close()

    def close(self):
        self.connected = False
        self.transport.close()

    def encode(self, inbuf, timestamp=None):
        assert inbuf == b"" or inbuf[-1] != b"\n"

        if not timestamp:
            timestamp = int(time.time() * 1000 % 1e7)
        enc = inbuf + bytearray('\x18%d\x19' % timestamp, "ascii")
        padding = 12 - len(enc) % 12
        filler = random.sample(FILLER, padding)
        enc += bytearray(filler)

        buf = enc

        for i in range(0, len(buf), 12):
            buf[i + 11], buf[i] = buf[i], buf[i + 11]
            buf[i + 9], buf[i + 2] = buf[i + 2], buf[i + 9]
            buf[i + 7], buf[i + 4] = buf[i + 4], buf[i + 7]

        encode_offset = random.randrange(ENCODELEN)

        for i in range(len(buf)):
            buf[i] |= 0x80
            j = (i + encode_offset) % ENCODELEN
            buf[i] = (buf[i] ^ ENCODE[j]) - 32

        buf += bytearray([0x80 | encode_offset])
        return buf

    def get_init_string(self):
        """ timeseal header: TIMESTAMP|bruce|Linux gruber 2.6.15-gentoo-r1 #9
            PREEMPT Thu Feb 9 20:09:47 GMT 2006 i686 Intel(R) Celeron(R) CPU
            2.00GHz GenuineIntel GNU/Linux| 93049 """
        user = getpass.getuser()
        uname = ' '.join(list(platform.uname()))
        return "TIMESTAMP|" + user + "|" + uname + "|"

    def decode(self, buf, stateinfo=None):
        expected_table = b"[G]\n\r"
        # TODO: add support to FatICS's new zipseal protocol when it finalizes
        # expected_table = "[G]\n\r" if not self.FatICS else "[G]\r\n"
        final_state = len(expected_table)
        g_count = 0
        result = []

        if stateinfo:
            state, lookahead = stateinfo
        else:
            state, lookahead = 0, []

        lenb = len(buf)
        idx = 0
        while idx < lenb:
            buffer_item = buf[idx]
            expected = expected_table[state]
            if buffer_item == expected:
                state += 1
                if state == final_state:
                    g_count += 1
                    lookahead = []
                    state = 0
                else:
                    lookahead.append(buffer_item)
                idx += 1
            elif state == 0:
                result.append(buffer_item)
                idx += 1
            else:
                result.extend(lookahead)
                lookahead = []
                state = 0

        return bytearray(result), g_count, (state, lookahead)

    def write(self, string):
        logstr = "*" * len(string) if self.sensitive else string
        self.sensitive = False
        log.info(logstr, extra={"task": (self.name, "raw")})

        if self.timeseal:
            self.transport.write(self.encode(bytearray(string, "utf-8")) + b"\n")
        else:
            self.transport.write(string.encode() + b"\n")

    @asyncio.coroutine
    def readline(self):
        line = yield from self.readuntil(b"\n")
        return line

    @asyncio.coroutine
    def readuntil(self, until):
        if self.canceled:
            raise CanceledException()

        while True:
            i = self.buf.find(until)
            if self.ICC:
                l = sys.maxsize
                if i >= 0:
                    l = i
                j = self.buf.find(B_DTGR_END)
                if j >= 0:
                    l = min(l, j)
                k = self.buf.find(B_UNIT_END)
                if k >= 0:
                    l = min(l, k)
                if l != sys.maxsize and l != i:
                    stuff = self.buf[:l + 2]
                    self.buf = self.buf[l + 2:]
                    return str(stuff.strip().decode("latin_1"))
            if i >= 0:
                stuff = self.buf[:i + len(until)]
                self.buf = self.buf[i + len(until):]
                return str(stuff.strip().decode("latin_1"))
            yield from asyncio.sleep(0.01)

    def cook_some(self, data):
        recv = data
        if len(recv) == 0:
            return

        if not self.connected:
            log.debug(recv, extra={"task": (self.name, "raw")})
            self.buf += recv
            self.connected = True
            if b"FatICS" in self.buf:
                self.FatICS = True
            elif b"puertorico.com" in self.buf:
                self.USCN = True
                self.buf = self.buf.replace(IAC_WONT_ECHO, b"")
            elif b"chessclub.com" in self.buf:
                self.ICC = True
                self.buf = self.buf.replace(IAC_WONT_ECHO, b"")
            elif b"Starting FICS session" in self.buf:
                self.buf = self.buf.replace(IAC_WONT_ECHO, b"")
            self.connected_event.set()
        else:
            if self.timeseal:
                recv, g_count, self.stateinfo = self.decode(recv, self.stateinfo)
            recv = recv.replace(b"\r", b"")
            # enable this only for temporary debugging
            log.debug(recv, extra={"task": (self.name, "raw")})

            if self.timeseal:
                for i in range(g_count):
                    self.write(G_RESPONSE)

            self.buf += recv

    @asyncio.coroutine
    def read_until(self, *untils):
        if self.canceled:
            raise CanceledException()

        while True:
            for i, until in enumerate(untils):
                start = self.buf.find(bytearray(until, "ascii"))
                if start >= 0:
                    self.buf = self.buf[start:]
                    return i
                else:
                    not_find = "read_until:%s , got:'%s'" % (until, self.buf)
                    log.debug(not_find, extra={"task": (self.name, "raw")})
            yield from asyncio.sleep(1)

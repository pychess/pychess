import asyncio
import sys
import telnetlib
import random
import time
import platform
import subprocess
import getpass
import os
import shutil

from pychess.System.Log import log
from pychess.System.prefix import getEngineDataPrefix
from pychess.ic.icc import B_DTGR_END, B_UNIT_END

if not hasattr(asyncio.StreamReader, 'readuntil'):
    from pychess.System.readuntil import readuntil, _wait_for_data
    asyncio.StreamReader.readuntil = readuntil
    asyncio.StreamReader._wait_for_data = _wait_for_data

ENCODE = [ord(i) for i in "Timestamp (FICS) v1.0 - programmed by Henrik Gram."]
ENCODELEN = len(ENCODE)
G_RESPONSE = "\x029"
FILLER = b"1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
IAC_WONT_ECHO = b''.join([telnetlib.IAC, telnetlib.WONT, telnetlib.ECHO])

_DEFAULT_LIMIT = 2 ** 16


class CanceledException(Exception):
    pass


class ICSStreamReader(asyncio.StreamReader):
    def __init__(self, limit, loop, connected_event, name):
        asyncio.StreamReader.__init__(self, limit=limit, loop=loop)
        self.connected_event = connected_event
        self.name = name

    @asyncio.coroutine
    def read_until(self, *untils):
        while True:
            for i, until in enumerate(untils):
                start = self._buffer.find(bytearray(until, "ascii"))
                if start >= 0:
                    self._buffer = self._buffer[start:]
                    return i
                else:
                    not_find = "read_until:%s , got:'%s'" % (until, self._buffer)
                    log.debug(not_find, extra={"task": (self.name, "raw")})

            yield from self._wait_for_data('read_until')


class ICSStreamReaderProtocol(asyncio.StreamReaderProtocol):
    def __init__(self, stream_reader, client_connected_cb, loop, name, timeseal):
        asyncio.StreamReaderProtocol.__init__(self, stream_reader, client_connected_cb=client_connected_cb, loop=loop)
        self.name = name
        self.timeseal = timeseal
        self.connected = False
        self.stateinfo = None

    def data_received(self, data):
        cooked = self.cook_some(data)
        self._stream_reader.feed_data(cooked)

    def cook_some(self, data):
        if not self.connected:
            log.debug(data, extra={"task": (self.name, "raw")})
            self.connected = True
            if b"FatICS" in data:
                self.FatICS = True
            elif b"puertorico.com" in data:
                self.USCN = True
                data = data.replace(IAC_WONT_ECHO, b"")
            elif b"chessclub.com" in data:
                self.ICC = True
                data = data.replace(IAC_WONT_ECHO, b"")
            elif b"Starting FICS session" in data:
                data = data.replace(IAC_WONT_ECHO, b"")
        else:
            if self.timeseal:
                data, g_count, self.stateinfo = self.decode(data, self.stateinfo)
            data = data.replace(b"\r", b"").replace(b"\x07", b"")
            # enable this only for temporary debugging
            log.debug(data, extra={"task": (self.name, "raw")})

            if self.timeseal:
                for i in range(g_count):
                    self._stream_writer.write(self.encode(bytearray(G_RESPONSE, "utf-8")) + b"\n")
        return data

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


# You can get ICC timestamp from
# https://www.chessclub.com/user/resources/icc/timestamp/
if sys.platform == "win32":
    timestamp = "timestamp_win32.exe"
else:
    timestamp = "timestamp_linux_2.6.8"

altpath = getEngineDataPrefix()
timestamp_path = shutil.which(timestamp, os.X_OK, path=altpath)


class ICSTelnet():
    sensitive = False

    def __init__(self, timeseal):
        self.name = ""
        self.connected = False
        self.canceled = False
        self.FatICS = False
        self.USCN = False
        self.ICC = False
        self.timeseal = timeseal
        self.ICC_buffer = ""

    @asyncio.coroutine
    def start(self, host, port, connected_event):
        if self.canceled:
            raise CanceledException()
        self.port = port
        self.host = host
        self.connected_event = connected_event

        self.name = host

        if host == "chessclub.com":
            self.ICC = True

            if self.timeseal and timestamp_path is not None:
                self.host = "127.0.0.1"
                self.port = 5500
                try:
                    if sys.platform == "win32":
                        # To prevent engines opening console window
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    else:
                        startupinfo = None
                    create = asyncio.create_subprocess_exec(* ["%s" % timestamp_path, "-p", "%s" % self.port], startupinfo=startupinfo)
                    self.timestamp_proc = yield from create
                    log.info("%s started OK" % timestamp_path)
                except OSError as err:
                    log.info("Can't start %s OSError: %s %s" % (timestamp_path, err.errno, err.strerror))
                    self.port = port
                    self.host = host
            else:
                log.info("%s not found" % timestamp_path)

            self.timeseal = False

        def cb(reader, writer):
            reader.stream_writer = writer
            reader.connected_event.set()

        loop = asyncio.get_event_loop()
        self.reader = ICSStreamReader(_DEFAULT_LIMIT, loop, self.connected_event, self.name)
        self.protocol = ICSStreamReaderProtocol(self.reader, cb, loop, self.name, self.timeseal)
        coro = loop.create_connection(lambda: self.protocol, self.host, self.port)
        self.transport, _protocol = yield from coro
        # writer = asyncio.StreamWriter(transport, protocol, reader, loop)

        if self.timeseal:
            self.write(self.get_init_string())

    def cancel(self):
        self.canceled = True
        self.close()

    def close(self):
        if self.protocol.connected:
            self.protocol.connected = False
            self.transport.close()

    def get_init_string(self):
        """ timeseal header: TIMESTAMP|bruce|Linux gruber 2.6.15-gentoo-r1 #9
            PREEMPT Thu Feb 9 20:09:47 GMT 2006 i686 Intel(R) Celeron(R) CPU
            2.00GHz GenuineIntel GNU/Linux| 93049 """
        user = getpass.getuser()
        uname = ' '.join(list(platform.uname()))
        return "TIMESTAMP|" + user + "|" + uname + "|"

    def write(self, string):
        logstr = "*" * len(string) if self.sensitive else string
        self.sensitive = False
        log.info(logstr, extra={"task": (self.name, "raw")})

        if self.timeseal:
            self.transport.write(self.protocol.encode(bytearray(string, "utf-8")) + b"\n")
        else:
            self.transport.write(string.encode() + b"\n")

    @asyncio.coroutine
    def readline(self):
        if self.canceled:
            raise CanceledException()

        if self.ICC:
            line = yield from self.readuntil(b"\n")
            return line.strip()
        else:
            line = yield from self.reader.readline()
            return line.decode("latin_1").strip()

    @asyncio.coroutine
    def readuntil(self, until):
        if self.canceled:
            raise CanceledException()

        if self.ICC:
            if len(self.ICC_buffer) == 0:
                self.ICC_buffer = yield from self.reader.readuntil(until)
            i = self.ICC_buffer.find(until)
            m = sys.maxsize
            if i >= 0:
                m = i
            j = self.ICC_buffer.find(B_DTGR_END)
            if j >= 0:
                m = min(m, j)
            k = self.ICC_buffer.find(B_UNIT_END)
            if k >= 0:
                m = min(m, k)
            if m != sys.maxsize:
                if m == i:
                    stuff = self.ICC_buffer[:m + len(until)]
                    self.ICC_buffer = self.ICC_buffer[m + len(until):]
                    return stuff.decode("latin_1")
                else:
                    stuff = self.ICC_buffer[:m + 2]
                    self.ICC_buffer = self.ICC_buffer[m + 2:]
                    return stuff.decode("latin_1")
            else:
                return ""
        else:
            data = yield from self.reader.readuntil(until)
            return data.decode("latin_1")

    @asyncio.coroutine
    def read_until(self, *untils):
        if self.canceled:
            raise CanceledException()

        ret = yield from self.reader.read_until(*untils)
        return ret

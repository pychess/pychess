from __future__ import print_function

import errno
import socket
import telnetlib
import random
import time
import platform
import getpass

from pychess.System.Log import log

ENCODE = [ord(i) for i in "Timestamp (FICS) v1.0 - programmed by Henrik Gram."]
ENCODELEN = len(ENCODE)
G_RESPONSE = "\x029"
FILLER = b"1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
IAC_WONT_ECHO = b''.join([telnetlib.IAC, telnetlib.WONT, telnetlib.ECHO])


class CanceledException(Exception):
    pass


class TimeSeal(object):
    BUFFER_SIZE = 4096
    sensitive = False

    def __init__(self):
        self.name = ""
        self.connected = False
        self.canceled = False
        self.FatICS = False
        self.USCN = False
        self.buf = bytearray(b"")
        self.writebuf = bytearray(b"")
        self.stateinfo = None
        self.sock = None

    def open(self, host, port):
        if self.canceled:
            raise CanceledException()

        self.port = port
        self.host = host
        self.name = host

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        try:
            self.sock.connect((host, port))
        except socket.error as err:
            if err.errno != errno.EINPROGRESS:
                raise
        self.sock.settimeout(None)
        print(self.get_init_string(), file=self)
        self.cook_some()

    def cancel(self):
        self.canceled = True
        self.close()

    def close(self):
        self.connected = False
        try:
            self.sock.close()
        except AttributeError:
            pass

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
        self.writebuf += bytearray(string, "utf-8")
        if b"\n" not in self.writebuf:
            return
        if not self.connected:
            return

        i = self.writebuf.rfind(b"\n")
        string = self.writebuf[:i]
        self.writebuf = self.writebuf[i + 1:]

        logstr = "*" * len(string) if self.sensitive else string
        self.sensitive = False
        log.info(logstr, extra={"task": (self.name, "raw")})
        string = self.encode(string)
        try:
            self.sock.send(string + b"\n")
        except:
            pass

    def readline(self):
        return self.readuntil(b"\n")

    def readuntil(self, until):
        if self.canceled:
            raise CanceledException()

        while True:
            i = self.buf.find(until)
            if i >= 0:
                stuff = self.buf[:i + len(until)]
                self.buf = self.buf[i + len(until):]
                return str(stuff.strip().decode("latin_1"))
            self.cook_some()

    def cook_some(self):
        recv = self.sock.recv(self.BUFFER_SIZE)
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
            elif b"Starting FICS session" in self.buf:
                self.buf = self.buf.replace(IAC_WONT_ECHO, b"")
        else:
            recv, g_count, self.stateinfo = self.decode(recv, self.stateinfo)
            recv = recv.replace(b"\r", b"")
            # enable this only for temporary debugging
            # log.debug(recv, extra={"task": (self.name, "raw")})

            for i in range(g_count):
                print(G_RESPONSE, file=self)

            self.buf += recv

    def read_until(self, *untils):
        if self.canceled:
            raise CanceledException()

        while True:
            for i, until in enumerate(untils):
                start = self.buf.find(bytearray(until, "ascii"))
                if start >= 0:
                    self.buf = self.buf[:start]
                    return i
                else:
                    not_find = "read_until:%s , got:'%s'" % (until, self.buf)
                    log.debug(not_find, extra={"task": (self.name, "raw")})
            self.cook_some()

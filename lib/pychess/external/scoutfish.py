#!/usr/bin/env python

import json
import os
import re

import pexpect
from pexpect.popen_spawn import PopenSpawn

from pychess.Players.ProtocolEngine import TIME_OUT_SECOND

PGN_HEADERS_REGEX = re.compile(r"\[([A-Za-z0-9_]+)\s+\"(.*)\"\]")


class Scoutfish:
    def __init__(self, engine=''):
        if not engine:
            engine = './scoutfish'
        self.p = PopenSpawn(engine, timeout=TIME_OUT_SECOND, encoding="utf-8")
        self.wait_ready()
        self.pgn = ''
        self.db = ''

    def wait_ready(self):
        self.p.sendline('isready')
        self.p.expect(u'readyok')

    def open(self, pgn):
        '''Open a PGN file and create an index if not exsisting'''
        if not os.path.isfile(pgn):
            raise NameError("File {} does not exsist".format(pgn))
        pgn = os.path.normcase(pgn)
        self.pgn = pgn
        self.db = os.path.splitext(pgn)[0] + '.scout'
        if not os.path.isfile(self.db):
            result = self.make()
            self.db = result['DB file']

    def close(self):
        '''Terminate scoutfish. Not really needed: engine will terminate as
           soon as pipe is closed, i.e. when we exit.'''
        self.p.sendline('quit')
        self.p.expect(pexpect.EOF)
        self.pgn = ''
        self.db = ''

    def make(self):
        '''Make an index out of a pgn file. Normally called by open()'''
        if not self.pgn:
            raise NameError("Unknown DB, first open a PGN file")
        cmd = 'make ' + self.pgn
        self.p.sendline(cmd)
        self.wait_ready()
        s = '{' + self.p.before.split('{')[1]
        s = s.replace('\\', r'\\')  # Escape Windows's path delimiter
        result = json.loads(s)
        self.p.before = ''
        return result

    def setoption(self, name, value):
        '''Set an option value, like threads number'''
        cmd = "setoption name {} value {}".format(name, value)
        self.p.sendline(cmd)
        self.wait_ready()

    def scout(self, q):
        '''Run query defined by 'q' dict. Result will be a dict too'''
        if not self.db:
            raise NameError("Unknown DB, first open a PGN file")
        j = json.dumps(q)
        cmd = "scout {} {}".format(self.db, j)
        self.p.sendline(cmd)
        self.wait_ready()
        result = json.loads(self.p.before)
        self.p.before = ''
        return result

    def scout_raw(self, q):
        '''Run query defined by 'q' dict. Result will be full output'''
        if not self.db:
            raise NameError("Unknown DB, first open a PGN file")
        j = json.dumps(q)
        cmd = "scout {} {}".format(self.db, j)
        self.p.sendline(cmd)
        self.wait_ready()
        result = self.p.before
        self.p.before = ''
        return result

    def get_games(self, matches):
        '''Retrieve the PGN games specified in the offset list. Games are
           added to each list item with a 'pgn' key'''
        if not self.pgn:
            raise NameError("Unknown DB, first open a PGN file")
        with open(self.pgn, "rU") as f:
            for match in matches:
                f.seek(match['ofs'])
                game = ''
                for line in f:
                    if line.startswith('[Event "'):
                        if game:
                            break  # Second one, start of next game
                        else:
                            game = line  # First occurence
                    elif game:
                        game += line
                match['pgn'] = game.strip()
        return matches

    def get_header(self, pgn):
        '''Return a dict with just header information out of a pgn game. The
           pgn tags are supposed to be consecutive'''
        header = {}
        for line in pgn.splitlines():
            line = line.strip()
            if line.startswith('[') and line.endswith(']'):
                tag_match = PGN_HEADERS_REGEX.match(line)
                if tag_match:
                    header[tag_match.group(1)] = tag_match.group(2)
            else:
                break
        return header

    def get_game_headers(self, matches):
        '''Return a list of headers out of a list of pgn games. It is defined
           to be compatible with the return value of get_games()'''
        headers = []
        for match in matches:
            pgn = match['pgn']
            h = self.get_header(pgn)
            headers.append(h)
        return headers

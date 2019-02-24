#!/usr/bin/env python

import json
import os
import re

import pexpect
from pexpect.popen_spawn import PopenSpawn

from pychess.Players.ProtocolEngine import TIME_OUT_SECOND

PGN_HEADERS_REGEX = re.compile(r"\[([A-Za-z0-9_]+)\s+\"(.*)\"\]")


class Parser:
    def __init__(self, engine=''):
        if not engine:
            engine = './parser'
        self.p = PopenSpawn(engine, timeout=TIME_OUT_SECOND, encoding="utf-8")
        self.pgn = ''
        self.db = ''

    def wait_ready(self):
        self.p.sendline('isready')
        self.p.expect(u'readyok')

    def open(self, pgn, full=True):
        '''Open a PGN file and create an index if not exsisting'''
        if not os.path.isfile(pgn):
            raise NameError("File {} does not exsist".format(pgn))
        pgn = os.path.normcase(pgn)
        self.pgn = pgn
        self.db = os.path.splitext(pgn)[0] + '.bin'
        if not os.path.isfile(self.db):
            result = self.make(full)
            self.db = result['Book file']

    def close(self):
        '''Terminate chess_db. Not really needed: engine will terminate as
           soon as pipe is closed, i.e. when we exit.'''
        self.p.sendline('quit')
        self.p.expect(pexpect.EOF)
        self.pgn = ''
        self.db = ''

    def make(self, full=True):
        '''Make an index out of a pgn file'''
        if not self.pgn:
            raise NameError("Unknown DB, first open a PGN file")
        cmd = 'book ' + self.pgn
        if full:
            cmd += ' full'
        self.p.sendline(cmd)
        self.wait_ready()
        s = '{' + self.p.before.split('{')[1]
        s = s.replace('\\', r'\\')  # Escape Windows's path delimiter
        result = json.loads(s)
        self.p.before = ''
        return result

    def find(self, fen, limit=10, skip=0):
        '''Find all games with positions equal to fen'''
        if not self.db:
            raise NameError("Unknown DB, first open a PGN file")
        cmd = "find {} limit {} skip {} {}".format(self.db, limit, skip, fen)
        self.p.sendline(cmd)
        self.wait_ready()
        result = json.loads(self.p.before)
        self.p.before = ''
        return result

    def get_games(self, list):
        '''Retrieve the PGN games specified in the offset list'''
        if not self.pgn:
            raise NameError("Unknown DB, first open a PGN file")
        pgn = []
        with open(self.pgn, "r") as f:
            for ofs in list:
                f.seek(ofs)
                game = ''
                for line in f:
                    if line.startswith('[Event "'):
                        if game:
                            break  # Second one, start of next game
                        else:
                            game = line  # First occurence
                    elif game:
                        game += line
                pgn.append(game.strip())
        return pgn

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

    def get_game_headers(self, list):
        '''Return a list of headers out of a list of pgn games'''
        headers = []
        for pgn in list:
            h = self.get_header(pgn)
            headers.append(h)
        return headers

import os
import re
import json
from urllib.request import Request, urlopen
from urllib.parse import urlparse, parse_qs
from html.parser import HTMLParser
import asyncio
import websockets
import base64
import string
import random

from pychess import VERSION
from pychess.Utils.const import FISCHERRANDOMCHESS
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import parseAny, toSAN
from pychess.System.Log import log

# import pdb
# def _(p):
#     return p
# VERSION = '1.0'
# import ssl
# ssl._create_default_https_context = ssl._create_unverified_context


TYPE_NONE, TYPE_GAME, TYPE_STUDY, TYPE_PUZZLE = range(4)


# Abstract class to download a game from the Internet
class InternetGameInterface:
    # Internal
    def __init__(self):
        self.id = None
        self.userAgent = 'PyChess %s' % VERSION

    def is_enabled(self):
        return True

    def get_game_id(self):
        return self.id

    def reacts_to(self, url, host):
        # Verify the hostname
        if url is None:
            return False
        parsed = urlparse(url)
        if parsed.netloc.lower() not in ['www.' + host.lower(), host.lower()]:
            return False

        # Any page is valid
        self.id = url
        return True

    def json_loads(self, data):
        try:
            if data is None or data == '':
                return None
            return json.loads(data)
        except ValueError:
            return None

    def json_field(self, data, path):
        if data is None or data == '':
            return ''
        keys = path.split('/')
        value = data
        for key in keys:
            if key in value:
                value = value[key]
            else:
                return ''
        if value is None:
            return ''
        else:
            return value

    def read_data(self, response):
        # Check
        if response is None:
            return None
        bytes = response.read()

        # Decode
        cs = response.info().get_content_charset()
        if cs is not None:
            data = bytes.decode(cs)
        else:
            try:
                data = bytes.decode('utf-8')
            except Exception:
                try:
                    data = bytes.decode('latin-1')
                except Exception:
                    data = None

        # Result
        data = data.replace("\ufeff", "").replace("\r", '').strip()
        if data == '':
            return None
        else:
            return data

    def download(self, url, userAgent=False):
        # Check
        if url is None or url == '':
            return None

        # Download
        try:
            log.debug('Downloading game: %s' % url)
            if userAgent:
                req = Request(url, headers={'User-Agent': self.userAgent})
                response = urlopen(req)
            else:
                response = urlopen(url)
            return self.read_data(response)
        except Exception as exception:
            log.debug('Exception raised: %s' % repr(exception))
            return None

    def download_list(self, links, userAgent=False):
        pgn = ''
        for i, link in enumerate(links):
            data = self.download(link, userAgent)
            if data not in [None, '']:
                pgn += '%s\n\n' % data
            if i >= 10:                             # Anti-flood
                break
        if pgn == '':
            return None
        else:
            return pgn

    def async_from_sync(self, coro):
        curloop = asyncio.get_event_loop()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(coro)
        asyncio.set_event_loop(curloop)
        return result

    def rebuild_pgn(self, game):
        # Check
        if game is None or game == '' or '_moves' not in game or game['_moves'] == '':
            return None

        # Header
        pgn = ''
        for e in game:
            if e[:1] != '_' and game[e] not in [None, '']:
                pgn += '[%s "%s"]\n' % (e, game[e])
        if pgn == '':
            pgn = '[Annotator "%s"]\n' % self.userAgent
        pgn += "\n"

        # Body
        if '_url' in game:
            pgn += "{%s}\n" % game['_url']
        if '_moves' in game:
            pgn += '%s ' % game['_moves']
        if '_reason' in game:
            pgn += '{%s} ' % game['_reason']
        if 'Result' in game:
            pgn += '%s ' % game['Result']
        return pgn.strip()

    # External
    def get_description(self):
        pass

    def assign_game(self, url):
        pass

    def download_game(self):
        pass


# Lichess.org
class InternetGameLichess(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.url_type = TYPE_NONE
        self.url_tld = 'org'

    def get_description(self):
        return 'Lichess.org -- %s' % _('Download link')

    def assign_game(self, url):
        # Retrieve the ID of the study
        rxp = re.compile('^https?:\/\/([\S]+\.)?lichess\.(org|dev)\/study\/([a-z0-9]+(\/[a-z0-9]+)?)(\.pgn)?\/?([\S\/]+)?$', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            gid = m.group(3)
            if len(gid) in [8, 17]:
                self.url_type = TYPE_STUDY
                self.id = gid
                self.url_tld = m.group(2)
                return True

        # Retrieve the ID of the puzzle
        rxp = re.compile('^https?:\/\/([\S]+\.)?lichess\.(org|dev)\/training\/([0-9]+|daily)[\/\?\#]?', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            gid = m.group(3)
            if (gid.isdigit() and gid != '0') or gid == 'daily':
                self.url_type = TYPE_PUZZLE
                self.id = gid
                self.url_tld = m.group(2)
                return True

        # Retrieve the ID of the game
        rxp = re.compile('^https?:\/\/([\S]+\.)?lichess\.(org|dev)\/(game\/export\/)?([a-z0-9]+)\/?([\S\/]+)?$', re.IGNORECASE)  # More permissive
        m = rxp.match(url)
        if m is not None:
            gid = m.group(4)
            if len(gid) == 8:
                self.url_type = TYPE_GAME
                self.id = gid
                self.url_tld = m.group(2)
                return True

        # Nothing found
        return False

    def download_game(self):
        # Check
        if None in [self.id, self.url_tld]:
            return None

        # Logic for the games
        if self.url_type == TYPE_GAME:
            url = 'https://lichess.%s/game/export/%s?literate=1' % (self.url_tld, self.id)
            return self.download(url)

        # Logic for the studies
        elif self.url_type == TYPE_STUDY:
            url = 'https://lichess.%s/study/%s.pgn' % (self.url_tld, self.id)
            return self.download(url, userAgent=True)

        # Logic for the puzzles
        elif self.url_type == TYPE_PUZZLE:
            url = 'https://lichess.%s/training/%s' % (self.url_tld, self.id)
            page = self.download(url)
            if page is None:
                return None

            # Extract the JSON
            page = page.replace("\n", '')
            pos1 = page.find("lichess.puzzle =")
            if pos1 == -1:
                return None
            pos1 = page.find('"game"', pos1 + 1)
            if pos1 == -1:
                return None
            c = 1
            pos2 = pos1
            while pos2 < len(page):
                pos2 += 1
                if page[pos2] == '{':
                    c += 1
                if page[pos2] == '}':
                    c -= 1
                if c == 0:
                    break
            if c != 0:
                return None

            # Header
            bourne = page[pos1 - 1:pos2 + 1]
            chessgame = self.json_loads(bourne)
            puzzle = self.json_field(chessgame, 'puzzle')
            if puzzle == '':
                return None
            game = {}
            game['_url'] = 'https://lichess.org/%s#%s' % (self.json_field(puzzle, 'gameId'), self.json_field(puzzle, 'initialPly'))
            game['Site'] = 'lichess.org'
            rating = self.json_field(puzzle, 'rating')
            game['Event'] = 'Puzzle %d, rated %s' % (self.json_field(puzzle, 'id'), rating)
            game['Result'] = '*'
            game['X_ID'] = self.json_field(puzzle, 'id')
            game['X_TimeControl'] = self.json_field(chessgame, 'game/clock')
            game['X_Rating'] = rating
            game['X_Attempts'] = self.json_field(puzzle, 'attempts')
            game['X_Vote'] = self.json_field(puzzle, 'vote')

            # Players
            players = self.json_field(chessgame, 'game/players')
            if not isinstance(players, list):
                return None
            for p in players:
                if p['color'] == 'white':
                    t = 'White'
                elif p['color'] == 'black':
                    t = 'Black'
                else:
                    return None
                pos1 = p['name'].find(' (')
                if pos1 == -1:
                    game[t] = p['name']
                else:
                    game[t] = p['name'][:pos1]
                    game[t + 'Elo'] = p['name'][pos1 + 2:-1]

            # Moves
            moves = self.json_field(chessgame, 'game/treeParts')
            if not isinstance(moves, list):
                return None
            game['_moves'] = ''
            for m in moves:
                if m['ply'] in [0, '0']:
                    game['SetUp'] = '1'
                    game['FEN'] = m['fen']
                else:
                    game['_moves'] += '%s ' % m['san']

            # Solution
            game['_moves'] += ' {Solution: '
            puzzle = self.json_field(puzzle, 'branch')
            while True:
                game['_moves'] += '%s ' % self.json_field(puzzle, 'san')
                puzzle = self.json_field(puzzle, 'children')
                if len(puzzle) == 0:
                    break
                puzzle = puzzle[0]
            game['_moves'] += '}'

            # Rebuild the PGN game
            return self.rebuild_pgn(game)

        else:
            return None  # Never reached


# ChessGames.com
class InternetGameChessgames(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.computer = False

    def get_description(self):
        return 'ChessGames.com -- %s' % _('Download link')

    def assign_game(self, url):
        # Verify the hostname
        parsed = urlparse(url)
        if parsed.netloc.lower() not in ['www.chessgames.com', 'chessgames.com']:
            return False

        # Read the arguments
        args = parse_qs(parsed.query)
        if 'gid' in args:
            gid = args['gid'][0]
            if gid.isdigit() and gid != '0':
                self.id = gid
                self.computer = ('comp' in args) and (args['comp'][0] == '1')
                return True
        return False

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # First try with computer analysis
        url = 'http://www.chessgames.com/pgn/pychess.pgn?gid=' + self.id
        if self.computer:
            pgn = self.download(url + '&comp=1')
            if pgn in [None, ''] or 'NO SUCH GAME' in pgn:
                self.computer = False
            else:
                return pgn

        # Second try without computer analysis
        if not self.computer:
            pgn = self.download(url)
            if pgn in [None, ''] or 'NO SUCH GAME' in pgn:
                return None
            else:
                return pgn


# FicsGames.org
class InternetGameFicsgames(InternetGameInterface):
    def get_description(self):
        return 'FicsGames.org -- %s' % _('Download link')

    def assign_game(self, url):
        # Verify the URL
        parsed = urlparse(url)
        if parsed.netloc.lower() not in ['www.ficsgames.org', 'ficsgames.org'] or 'show' not in parsed.path.lower():
            return False

        # Read the arguments
        args = parse_qs(parsed.query)
        if 'ID' in args:
            gid = args['ID'][0]
            if gid.isdigit() and gid != '0':
                self.id = gid
                return True
        return False

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download
        pgn = self.download('http://ficsgames.org/cgi-bin/show.cgi?ID=%s;action=save' % self.id)
        if pgn in [None, ''] or 'not found in GGbID' in pgn:
            return None
        else:
            return pgn


# ChessTempo.com
class InternetGameChesstempo(InternetGameInterface):
    def get_description(self):
        return 'ChessTempo.com -- %s' % _('Download link')

    def assign_game(self, url):
        rxp = re.compile('^https?:\/\/(\S+\.)?chesstempo\.com\/gamedb\/game\/(\d+)\/?([\S\/]+)?$', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            gid = str(m.group(2))
            if gid.isdigit() and gid != '0':
                self.id = gid
                return True
        return False

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download
        pgn = self.download('http://chesstempo.com/requests/download_game_pgn.php?gameids=%s' % self.id, userAgent=True)  # Else a random game is retrieved
        if pgn is None or len(pgn) <= 128:
            return None
        else:
            return pgn


# Chess24.com
class InternetGameChess24(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.use_an = True  # True to rebuild a readable PGN

    def get_description(self):
        return 'Chess24.com -- %s' % _('HTML parsing')

    def assign_game(self, url):
        rxp = re.compile('^https?:\/\/chess24\.com\/[a-z]+\/(analysis|game|download-game)\/([a-z0-9\-_]+)[\/\?\#]?', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            gid = str(m.group(2))
            if len(gid) == 22:
                self.id = gid
                return True
        return False

    def download_game(self):
        # Download the page
        if self.id is None:
            return None
        url = 'https://chess24.com/en/game/%s' % self.id
        page = self.download(url, userAgent=True)  # Else HTTP 403 Forbidden
        if page is None:
            return None

        # Extract the JSON of the game
        lines = page.split("\n")
        for line in lines:
            line = line.strip()
            pos1 = line.find('.initGameSession({')
            pos2 = line.find('});', pos1)
            if -1 in [pos1, pos2]:
                continue

            # Read the game from JSON
            bourne = self.json_loads(line[pos1 + 17:pos2 + 1])
            chessgame = self.json_field(bourne, 'chessGame')
            moves = self.json_field(chessgame, 'moves')
            if '' in [chessgame, moves]:
                continue

            # Build the header of the PGN file
            game = {}
            game['_moves'] = ''
            game['_url'] = url
            game['Event'] = self.json_field(chessgame, 'meta/Event')
            game['Site'] = self.json_field(chessgame, 'meta/Site')
            game['Date'] = self.json_field(chessgame, 'meta/Date')
            game['Round'] = self.json_field(chessgame, 'meta/Round')
            game['White'] = self.json_field(chessgame, 'meta/White/Name')
            game['WhiteElo'] = self.json_field(chessgame, 'meta/White/Elo')
            game['Black'] = self.json_field(chessgame, 'meta/Black/Name')
            game['BlackElo'] = self.json_field(chessgame, 'meta/Black/Elo')
            game['Result'] = self.json_field(chessgame, 'meta/Result')

            # Build the PGN
            board = LBoard(variant=FISCHERRANDOMCHESS)
            head_complete = False
            for move in moves:
                # Info from the knot
                kid = self.json_field(move, 'knotId')
                if kid == '':
                    break
                kmove = self.json_field(move, 'move')

                # FEN initialization
                if kid == 0:
                    kfen = self.json_field(move, 'fen')
                    if kfen == '':
                        break
                    try:
                        board.applyFen(kfen)
                    except Exception:
                        return None
                    game['Variant'] = 'Fischerandom'
                    game['SetUp'] = '1'
                    game['FEN'] = kfen
                    head_complete = True
                else:
                    if not head_complete:
                        return None

                    # Execution of the move
                    if kmove == '':
                        break
                    try:
                        if self.use_an:
                            kmove = parseAny(board, kmove)
                            game['_moves'] += toSAN(board, kmove) + ' '
                            board.applyMove(kmove)
                        else:
                            game['_moves'] += kmove + ' '
                    except Exception:
                        return None

            # Rebuild the PGN game
            return self.rebuild_pgn(game)
        return None


# 365chess.com
class InternetGame365chess(InternetGameInterface):
    def get_description(self):
        return '365chess.com -- %s' % _('HTML parsing')

    def assign_game(self, url):
        # Verify the URL
        parsed = urlparse(url)
        if parsed.netloc.lower() not in ['www.365chess.com', '365chess.com'] or 'view_game' not in parsed.path.lower():
            return False

        # Read the arguments
        args = parse_qs(parsed.query)
        if 'g' in args:
            gid = args['g'][0]
            if gid.isdigit() and gid != '0':
                self.id = gid
                return True
        return False

    def download_game(self):
        # Download
        if self.id is None:
            return None
        url = 'https://www.365chess.com/view_game.php?g=%s' % self.id
        page = self.download(url)
        if page is None:
            return None

        # Played moves
        game = {}
        pos1 = page.find(".ApplyPgnMoveText('")
        pos2 = page.find("')", pos1)
        if -1 in [pos1, pos2]:
            return None
        game['_moves'] = page[pos1 + 19:pos2]

        # Header
        game['_url'] = url
        lines = page.split("\n")
        for line in lines:
            line = line.strip()

            if line.startswith('<tr><td><h1>') and line.endswith('</h1></td></tr>'):
                rxp = re.compile('^([\w\-\s]+) \(([0-9]+)\) vs\. ([\w\-\s]+) \(([0-9]+)\)$', re.IGNORECASE)
                m = rxp.match(line[12:-15])
                if m is None:
                    game['White'] = _('Unknown')
                    game['Black'] = _('Unknown')
                else:
                    game['White'] = str(m.group(1))
                    game['WhiteElo'] = str(m.group(2))
                    game['Black'] = str(m.group(3))
                    game['BlackElo'] = str(m.group(4))
                continue

            if line.startswith('<tr><td><h2>') and line.endswith('</h2></td></tr>'):
                list = line[12:-15].split(' &middot; ')
                game['Event'] = list[0]
                game['Opening'] = list[1]
                game['Result'] = list[2].replace('&frac12;', '1/2')
                continue

        # Rebuild the PGN game
        return self.rebuild_pgn(game)


# ChessPastebin.com
class InternetGameChesspastebin(InternetGameInterface):
    def get_description(self):
        return 'ChessPastebin.com -- %s' % _('HTML parsing')

    def assign_game(self, url):
        return self.reacts_to(url, 'chesspastebin.com')

    def download_game(self):
        # Download
        if self.id is None:
            return None
        page = self.download(self.id)
        if page is None:
            return None

        # Extract the game ID
        rxp = re.compile('.*?\<div id=\"([0-9]+)_board\"\>\<\/div\>.*?', flags=re.IGNORECASE)
        m = rxp.match(page.replace("\n", ''))
        if m is None:
            return None
        gid = m.group(1)

        # Definition of the parser
        class chesspastebinparser(HTMLParser):
            def __init__(self):
                HTMLParser.__init__(self)
                self.tag_ok = False
                self.pgn = None

            def handle_starttag(self, tag, attrs):
                if tag.lower() == 'div':
                    for k, v in attrs:
                        if k.lower() == 'id' and v == gid:
                            self.tag_ok = True

            def handle_data(self, data):
                if self.pgn is None and self.tag_ok:
                    self.pgn = data

        # Read the PGN
        parser = chesspastebinparser()
        parser.feed(page)
        pgn = parser.pgn
        if pgn is not None:  # Any game must start with '[' to be considered further as valid
            pgn = pgn.strip()
            if not pgn.startswith('['):
                pgn = "[Annotator \"ChessPastebin.com\"]\n%s" % pgn
        return pgn


# ChessBomb.com
class InternetGameChessbomb(InternetGameInterface):
    def get_description(self):
        return 'ChessBomb.com -- %s' % _('HTML parsing')

    def assign_game(self, url):
        return self.reacts_to(url, 'chessbomb.com')

    def download_game(self):
        # Download
        if self.id is None:
            return None
        url = self.id
        page = self.download(url, userAgent=True)  # Else HTTP 403 Forbidden
        if page is None:
            return None

        # Definition of the parser
        class chessbombparser(HTMLParser):
            def __init__(self):
                HTMLParser.__init__(self)
                self.last_tag = None
                self.json = None

            def handle_starttag(self, tag, attrs):
                self.last_tag = tag.lower()

            def handle_data(self, data):
                if self.json is None and self.last_tag == 'script':
                    pos1 = data.find('cbConfigData')
                    if pos1 == -1:
                        return
                    pos1 = data.find('"', pos1)
                    pos2 = data.find('"', pos1 + 1)
                    if -1 not in [pos1, pos2]:
                        try:
                            self.json = base64.b64decode(data[pos1 + 1:pos2]).decode().strip()
                            self.json = json.loads(self.json)
                        except Exception:
                            self.json = None
                            return

        # Get the JSON
        parser = chessbombparser()
        parser.feed(page)
        if parser.json is None:
            return None

        # Interpret the JSON
        header = self.json_field(parser.json, 'gameData/game')
        room = self.json_field(parser.json, 'gameData/room')
        moves = self.json_field(parser.json, 'gameData/moves')
        if '' in [header, room, moves]:
            return None

        game = {}
        game['_url'] = url
        game['Event'] = self.json_field(room, 'name')
        game['Site'] = self.json_field(room, 'officialUrl')
        game['Date'] = self.json_field(header, 'startAt')[:10]
        game['Round'] = self.json_field(header, 'roundSlug')
        game['White'] = self.json_field(header, 'white/name')
        game['WhiteElo'] = self.json_field(header, 'white/elo')
        game['Black'] = self.json_field(header, 'black/name')
        game['BlackElo'] = self.json_field(header, 'black/elo')
        game['Result'] = self.json_field(header, 'result')

        game['_moves'] = ''
        for move in moves:
            move = self.json_field(move, 'cbn')
            pos1 = move.find('_')
            if pos1 == -1:
                break
            game['_moves'] += move[pos1 + 1:] + ' '

        # Rebuild the PGN game
        return self.rebuild_pgn(game)


# TheChessWorld.com
class InternetGameThechessworld(InternetGameInterface):
    def get_description(self):
        return 'TheChessWorld.com -- %s' % _('Download link')

    def assign_game(self, url):
        return self.reacts_to(url, 'thechessworld.com')

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Find the links
        links = []
        if self.id.lower().endswith('.pgn'):
            links.append(self.id)
        else:
            # Download the page
            data = self.download(self.id)
            if data is None:
                return None

            # Finds the games
            rxp = re.compile(".*pgn_uri:.*'([^']+)'.*", re.IGNORECASE)
            list = data.split("\n")
            for line in list:
                m = rxp.match(line)
                if m is not None:
                    links.append('https://www.thechessworld.com' + m.group(1))

        # Collect the games
        return self.download_list(links)


# Chess.org
class InternetGameChessOrg(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.use_an = True  # True to rebuild a readable PGN

    def get_description(self):
        return 'Chess.org -- %s' % _('Websockets')

    def assign_game(self, url):
        rxp = re.compile('^https?:\/\/chess\.org\/play\/([a-f0-9\-]+)[\/\?\#]?', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            id = str(m.group(1))
            if len(id) == 36:
                self.id = id
                return True
        return False

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Fetch the page to retrieve the encrypted user name
        url = 'https://chess.org/play/%s' % self.id
        page = self.download(url)
        if page is None:
            return None
        lines = page.split("\n")
        name = ''
        for line in lines:
            pos1 = line.find('encryptedUsername')
            if pos1 != -1:
                pos1 = line.find("'", pos1)
                pos2 = line.find("'", pos1 + 1)
                if pos2 > pos1:
                    name = line[pos1 + 1:pos2]
                    break
        if name == '':
            return None

        # Random elements to get a unique URL
        rndI = random.randint(1, 1000)
        rndS = ''.join(random.choice(string.ascii_lowercase) for i in range(8))

        # Open a websocket to retrieve the chess data
        @asyncio.coroutine
        def coro():
            url = 'wss://chess.org:443/play-sockjs/%d/%s/websocket' % (rndI, rndS)
            log.debug('Websocket connecting to %s' % url)
            ws = yield from websockets.connect(url, origin="https://chess.org:443", close_timeout=5)
            try:
                # Server: Hello
                data = yield from ws.recv()
                if data != 'o':  # Open
                    yield from ws.close()
                    return None

                # Client: I am XXX, please open the game YYY
                yield from ws.send('["%s %s"]' % (name, self.id))
                data = yield from ws.recv()

                # Server: some data
                if data[:1] != 'a':
                    yield from ws.close()
                    return None
                return data[3:-2]
            finally:
                yield from ws.close()

        data = self.async_from_sync(coro())
        if data is None or data == '':
            return None

        # Parses the game
        chessgame = self.json_loads(data.replace('\\"', '"'))
        game = {}
        game['_url'] = url
        board = LBoard(variant=FISCHERRANDOMCHESS)

        # Player info
        if self.json_field(chessgame, 'creatorColor') == '1':  # White=1, Black=0
            creator = 'White'
            opponent = 'Black'
        else:
            creator = 'Black'
            opponent = 'White'
        game[creator] = self.json_field(chessgame, 'creatorId')
        elo = self.json_field(chessgame, 'creatorPoint')
        if elo not in ['', '0', 0]:
            game[creator + 'Elo'] = elo
        game[opponent] = self.json_field(chessgame, 'opponentId')
        elo = self.json_field(chessgame, 'opponentPoint')
        if elo not in ['', '0', 0]:
            game[opponent + 'Elo'] = elo

        # Game info
        startPos = self.json_field(chessgame, 'startPos')
        if startPos not in ['', 'startpos']:
            game['SetUp'] = '1'
            game['FEN'] = startPos
            game['Variant'] = 'Fischerandom'
            try:
                board.applyFen(startPos)
            except Exception:
                return None
        else:
            board.applyFen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w AHah - 0 1')
        time = self.json_field(chessgame, 'timeLimitSecs')
        inc = self.json_field(chessgame, 'timeBonusSecs')
        if '' not in [time, inc]:
            game['TimeControl'] = '%s+%s' % (time, inc)
        resultTable = [(0, '*', 'Game started'),
                       (1, '1-0', 'White checkmated'),
                       (2, '0-1', 'Black checkmated'),
                       (3, '1/2-1/2', 'Stalemate'),
                       (5, '1/2-1/2', 'Insufficient material'),
                       (8, '1/2-1/2', 'Mutual agreement'),
                       (9, '0-1', 'White resigned'),
                       (10, '1-0', 'Black resigned'),
                       (13, '1-0', 'White out of time'),
                       (14, '0-1', 'Black out of time')]  # TODO List to be completed
        state = self.json_field(chessgame, 'state')
        result = '*'
        reason = 'Unknown reason %d' % state
        for rtID, rtScore, rtMsg in resultTable:
            if rtID == state:
                result = rtScore
                reason = rtMsg
                break
        game['Result'] = result
        game['_reason'] = reason

        # Moves
        game['_moves'] = ''
        moves = self.json_field(chessgame, 'lans')
        if moves == '':
            return None
        moves = moves.split(' ')
        for move in moves:
            try:
                if self.use_an:
                    move = parseAny(board, move)
                    game['_moves'] += toSAN(board, move) + ' '
                    board.applyMove(move)
                else:
                    game['_moves'] += move + ' '
            except Exception:
                return None

        # Rebuild the PGN game
        return self.rebuild_pgn(game)


# Europe-Echecs.com
class InternetGameEuropeechecs(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)

    def get_description(self):
        return 'Europe-Echecs.com -- %s' % _('Download link')

    def assign_game(self, url):
        return self.reacts_to(url, 'europe-echecs.com')

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Find the links
        links = []
        if self.id.lower().endswith('.pgn'):
            links.append(self.id)
        else:
            # Download the page
            page = self.download(self.id)
            if page is None:
                return None

            # Find the chess widgets
            rxp = re.compile(".*class=\"cbwidget\"\s+id=\"([0-9a-f]+)_container\".*", re.IGNORECASE)
            list = page.split("\n")
            for line in list:
                m = rxp.match(line)
                if m is not None:
                    links.append('https://www.europe-echecs.com/embed/doc_%s.pgn' % m.group(1))

        # Collect the games
        return self.download_list(links)


# GameKnot.com
class InternetGameGameknot(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.use_an = True  # True to rebuild a readable PGN

    def get_description(self):
        return 'GameKnot.com -- %s' % _('HTML parsing')

    def assign_game(self, url):
        # Verify the URL
        parsed = urlparse(url)
        if parsed.netloc.lower() not in ['www.gameknot.com', 'gameknot.com']:
            return False
        if 'chess.pl' not in parsed.path.lower() and 'analyze-board.pl' not in parsed.path.lower():
            return False

        # Read the arguments
        args = parse_qs(parsed.query)
        if 'bd' in args:
            gid = args['bd'][0]
            if gid.isdigit() and gid != '0':
                self.id = gid
                return True
        return False

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download
        url = 'https://gameknot.com/analyze-board.pl?bd=%s' % self.id
        page = self.download(url, userAgent=True)
        if page is None:
            return None

        # Header
        game = {}
        structure = [('anbd_movelist', 's', '_moves'),
                     ('anbd_result', 'i', 'Result'),
                     ('anbd_player_w', 's', 'White'),
                     ('anbd_player_b', 's', 'Black'),
                     ('anbd_rating_w', 'i', 'WhiteElo'),
                     ('anbd_rating_b', 'i', 'BlackElo'),
                     ('anbd_title', 's', 'Event'),
                     ('anbd_timestamp', 's', 'Date'),
                     ('export_web_input_result_text', 's', '_reason')]
        for var, type, tag in structure:
            game[tag] = ''
        game['_url'] = url
        lines = page.split(';')
        for line in lines:
            for var, type, tag in structure:
                if var not in line.lower():
                    continue
                if type == 's':
                    pos1 = line.find("'")
                    pos2 = line.find("'", pos1 + 1)
                    if pos2 > pos1:
                        game[tag] = line[pos1 + 1:pos2]
                elif type == 'i':
                    pos1 = line.find("=")
                    if pos1 != -1:
                        txt = line[pos1 + 1:].strip()
                        if txt not in ['', '0']:
                            game[tag] = txt
                else:
                    return None
        if game['Result'] == '1':
            game['Result'] = '1-0'
        elif game['Result'] == '2':
            game['Result'] = '1/2-1/2'
        elif game['Result'] == '3':
            game['Result'] = '0-1'
        else:
            game['Result'] = '*'

        # Body
        board = LBoard()
        board.applyFen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
        moves = game['_moves'].split('-')
        game['_moves'] = ''
        for move in moves:
            if move == '':
                break
            try:
                if self.use_an:
                    kmove = parseAny(board, move)
                    game['_moves'] += toSAN(board, kmove) + ' '
                    board.applyMove(kmove)
                else:
                    game['_moves'] += move + ' '
            except Exception:
                return None

        # Rebuild the PGN game
        return self.rebuild_pgn(game)


# Chess.com
class InternetGameChessCom(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.url_type = None
        self.use_an = True  # True to rebuild a readable PGN

    def get_description(self):
        return 'Chess.com -- %s' % _('HTML parsing')

    def assign_game(self, url):
        rxp = re.compile('^https?:\/\/([\S]+\.)?chess\.com\/([a-z]+\/)?(live|daily)\/game\/([0-9]+)[\/\?\#]?', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            self.url_type = m.group(3)
            self.id = m.group(4)
            return True
        return False

    def download_game(self):
        # Check
        if None in [self.id, self.url_type]:
            return None

        # Download
        url = 'https://www.chess.com/%s/game/%s' % (self.url_type, self.id)
        page = self.download(url, userAgent=True)  # Else 403 Forbidden
        if page is None:
            return None

        # Logic for the live games
        if self.url_type.lower() == 'live':
            # Extract the JSON
            page = page.replace("\n", '')
            pos1 = page.find("init('live'")
            if pos1 == -1:
                return None
            pos1 = page.find('{', pos1 + 1)
            pos1 = page.find('{', pos1 + 1)
            if pos1 == -1:
                return None
            c = 1
            pos2 = pos1
            while pos2 < len(page):
                pos2 += 1
                if page[pos2] == '{':
                    c += 1
                if page[pos2] == '}':
                    c -= 1
                if c == 0:
                    break
            if c != 0:
                return None

            # Extract the PGN
            bourne = page[pos1:pos2 + 1].replace('&quot;', '"').replace('\\r', '')
            chessgame = self.json_loads(bourne)
            pgn = self.json_field(chessgame, 'pgn').replace('\\n', "\n")
            if pgn == '':
                return None
            else:
                return pgn

        # Logic for the daily games
        elif self.url_type.lower() == 'daily':
            return None

        else:
            return None  # Never reached


# Generic
class InternetGameGeneric(InternetGameInterface):
    def get_description(self):
        return 'Generic -- %s' % _('Various techniques')

    def assign_game(self, url):
        # Any page is valid
        self.id = url
        return True

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download
        req = Request(self.id, headers={'User-Agent': self.userAgent})
        response = urlopen(req)
        mime = response.info().get_content_type().lower()
        data = self.read_data(response)
        if data is None:
            return None

        # Chess file
        if mime == 'application/x-chess-pgn':
            return data

        # Web-page
        if mime == 'text/html':
            # Definition of the parser
            class linksParser(HTMLParser):
                def __init__(self):
                    HTMLParser.__init__(self)
                    self.links = []

                def handle_starttag(self, tag, attrs):
                    if tag.lower() == 'a':
                        for k, v in attrs:
                            if k.lower() == 'href':
                                v = v.strip()
                                u = urlparse(v)
                                if u.path.lower().endswith('.pgn'):
                                    self.links.append(v)

            # Read the links
            parser = linksParser()
            parser.feed(data)

            # Rebuild a full path
            base = urlparse(self.id)
            for i, link in enumerate(parser.links):
                e = urlparse(link)
                if e.netloc == '':
                    url = '%s://%s/%s' % (base.scheme, base.netloc, e.path)
                else:
                    url = link
                parser.links[i] = url

            # Collect the games
            return self.download_list(parser.links)
        return None


# Interface
chess_providers = [InternetGameLichess(),
                   InternetGameChessgames(),
                   InternetGameFicsgames(),
                   InternetGameChesstempo(),
                   InternetGameChess24(),
                   InternetGame365chess(),
                   InternetGameChesspastebin(),
                   InternetGameChessbomb(),
                   InternetGameThechessworld(),
                   InternetGameChessOrg(),
                   InternetGameEuropeechecs(),
                   InternetGameGameknot(),
                   InternetGameChessCom(),
                   InternetGameGeneric()]


# Get the list of chess providers
def get_internet_game_providers():
    list = [cp.get_description() for cp in chess_providers]
    list.sort()
    return list


# Retrieve a game from a URL
def get_internet_game_as_pgn(url):
    # Check the format
    if url is None:
        return None
    p = urlparse(url.strip())
    if '' in [p.scheme, p.netloc]:
        return None

    # Download a game for each provider
    for prov in chess_providers:
        if not prov.is_enabled():
            continue
        if prov.assign_game(url):
            try:
                pgn = prov.download_game()
            except Exception:
                pgn = None
            if pgn is None:
                continue

            # Verify that it starts with the correct magic character (ex.: "<" denotes an HTML content, "[" a chess game, etc...)
            pgn = pgn.strip()
            if not pgn.startswith('['):
                return None

            # Reorganize the spaces to bypass Scoutfish's limitation
            lc = len(pgn)
            while (True):
                pgn = pgn.replace("\n\n\n", "\n\n")
                lcn = len(pgn)
                if lcn == lc:
                    break
                lc = lcn

            # Extract the first game
            pos = pgn.find("\n\n[")  # TODO Support in-memory database to load several games at once
            if pos != -1:
                pgn = pgn[:pos]

            # Return the PGN with the local crlf
            return pgn.replace("\n", os.linesep)
    return None


# print(get_internet_game_as_pgn(''))

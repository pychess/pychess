import os
import re
import json
from urllib.request import Request, urlopen
from urllib.parse import urlparse, parse_qs, unquote, urlencode
from html import unescape
from html.parser import HTMLParser
import asyncio
import websockets
from base64 import b64decode
import string
from random import choice, randint

from pychess import VERSION
from pychess.Utils.const import CRAZYHOUSECHESS, FISCHERRANDOMCHESS, reprResult
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import parseAny, toSAN
from pychess.System.Log import log

# import pdb
# def _(p):
#     return p
# VERSION = '1.0'
# import ssl
# ssl._create_default_https_context = ssl._create_unverified_context  # Chess24, ICCF


TYPE_NONE, TYPE_GAME, TYPE_STUDY, TYPE_PUZZLE, TYPE_EVENT, TYPE_FEN = range(6)
CHESS960 = 'Fischerandom'
DEFAULT_BOARD = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

CAT_DL = _('Download link')
CAT_HTML = _('HTML parsing')
CAT_API = _('Application programming interface')
CAT_MISC = _('Various techniques')
CAT_WS = _('Websockets')


# Abstract class to download a game from the Internet
class InternetGameInterface:
    # Internal
    def __init__(self):
        ''' Initialize the common data that can be used in ALL the sub-classes. '''
        self.id = None
        self.allow_extra = False
        self.userAgent = 'PyChess %s' % VERSION
        self.use_an = True  # To rebuild a readable PGN where possible
        self.allow_octet_stream = False

    def is_enabled(self):
        ''' To disable a chess provider temporarily, override this method in the sub-class. '''
        return True

    def get_game_id(self):
        ''' Return the unique identifier of the game that was detected after a successful call to assign_game().
            The value is None if no game was found earlier. '''
        return self.id

    def reacts_to(self, url, host):
        ''' Return True if the URL belongs to the HOST (possibly equal to *). The sub-domains other than "www" are not supported.
            The method is used to accept any URL when a unique identifier cannot be extracted by assign_game(). '''
        # Verify the hostname
        if url is None:
            return False
        if host != '*':
            parsed = urlparse(url)
            if parsed.netloc.lower() not in ['www.' + host.lower(), host.lower()]:
                return False

        # Any page is valid
        self.id = url
        return True

    def json_loads(self, data):
        ''' Load a JSON and handle the errors.
            The value None is returned when the data are not relevant or misbuilt. '''
        try:
            if data in [None, '']:
                return None
            return json.loads(data)
        except ValueError:
            return None

    def json_field(self, data, path, default=''):
        ''' Conveniently read a field from a JSON data. The PATH is a key like "node1/node2/key".
            A blank string is returned in case of error. '''
        if data in [None, '']:
            return ''
        keys = path.split('/')
        value = data
        for key in keys:
            if key.startswith('[') and key.endswith(']'):
                try:
                    value = value[int(key[1:-1])]
                except (ValueError, TypeError, IndexError):
                    return ''
            else:
                if key in value:
                    value = value[key]
                else:
                    return ''
        return default if value in [None, ''] else value

    def read_data(self, response):
        ''' Read the data from an HTTP request and execute the charset conversion.
            The value None is returned in case of error. '''
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
                    log.debug('Error in the decoding of the data')
                    return None

        # Result
        data = data.replace("\ufeff", '').replace("\r", '').strip()
        if data == '':
            return None
        else:
            return data

    def expand_links(self, links, url):
        ''' Convert relative paths into full paths '''
        base = urlparse(url)
        for i, link in enumerate(links):
            e = urlparse(link)
            if e.netloc == '':
                if e.path.startswith('/'):
                    link = '%s://%s%s' % (base.scheme, base.netloc, e.path)
                else:
                    link = '%s://%s%s/%s' % (base.scheme, base.netloc, '/'.join(base.path.split('/')[:-1]), e.path)
            links[i] = link
        return list(dict.fromkeys(links))       # Without duplicate entries

    def download(self, url, userAgent=False):
        ''' Download the URL from the Internet.
            The USERAGENT is requested by some websites to make sure that you are not a bot.
            The value None is returned in case of error. '''
        # Check
        if url in [None, '']:
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
            log.debug('Exception raised: %s' % str(exception))
            return None

    def download_list(self, links, userAgent=False):
        ''' Download and concatenate the URL given in the array LINKS.
            The USERAGENT is requested by some websites to make sure that you are not a bot.
            The number of downloads is limited to 10.
            The downloads that failed are dropped silently.
            The value None is returned in case of no data or error. '''
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
        ''' The method is used for the WebSockets technique to call an asynchronous task from a synchronous task. '''
        # TODO Not working under Linux while PyChess GUI is running
        curloop = asyncio.get_event_loop()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(coro)
        loop.close()
        asyncio.set_event_loop(curloop)
        return result

    def send_xhr(self, url, postData, userAgent=False):
        ''' Call a target URL by submitting the POSTDATA.
            The USERAGENT is requested by some websites to make sure that you are not a bot.
            The value None is returned in case of error. '''
        # Check
        if url in [None, ''] or postData in [None, '']:
            return None

        # Call data
        try:
            log.debug('Calling API: %s' % url)
            if userAgent:
                req = Request(url, urlencode(postData).encode(), headers={'User-Agent': self.userAgent})
            else:
                req = Request(url, urlencode(postData).encode())
            response = urlopen(req)
            return self.read_data(response)
        except Exception as exception:
            log.debug('Exception raised: %s' % str(exception))
            return None

    def rebuild_pgn(self, game):
        ''' Return an object in PGN format.
            The keys starting with "_" are dropped silently.
            The key "_url" becomes the first comment.
            The key "_moves" contains the moves.
            The key "_reason" becomes the last comment. '''
        # Check
        if game is None or game == '' or '_moves' not in game or game['_moves'] == '':
            return None

        # Header
        pgn = ''
        for e in game:
            if e[:1] != '_' and game[e] not in [None, '']:
                pgn += '[%s "%s"]\n' % (e, game[e])
        if pgn == '':
            pgn = '[Annotator "PyChess %s"]\n' % VERSION
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

    def sanitize(self, pgn):
        ''' Modify the PGN output to comply with the expected format '''
        # Check
        if pgn in [None, '']:
            return None

        # Verify that it starts with the correct magic character (ex.: "<" denotes an HTML content, "[" a chess game, etc...)
        pgn = pgn.replace('\r', '').strip()
        if not pgn.startswith('['):
            return None

        # Reorganize the spaces to bypass Scoutfish's limitation
        while (True):
            lc = len(pgn)
            pgn = pgn.replace("\n\n\n", "\n\n")
            if len(pgn) == lc:
                break

        # Extract the first game
        pos = pgn.find("\n\n[")  # TODO Support in-memory database to load several games at once
        if pos != -1:
            pgn = pgn[:pos]

        # Variants
        pgn = pgn.replace('[Variant "Chess"]\n', '')

        # Return the PGN with the local crlf
        return pgn.replace("\n", os.linesep)

    def stripHtml(self, input):
        ''' Remove any HTML mark from the input parameter '''
        rxp = re.compile(r'<\/?[^<]+>', re.IGNORECASE)
        return rxp.sub('', input)

    def isFen(self, fen):
        ''' Test if the argument is a FEN position '''
        try:
            rxp = re.compile(r'^[kqbnrp1-8\/]+\s[w|b]\s[kq-]+\s[a-h-][1-8]?(\s[0-9]+)?(\s[0-9]+)?$', re.IGNORECASE)
            return rxp.match(fen) is not None
        except TypeError:
            return False

    # External
    def get_description(self):
        ''' (Abstract) Name of the chess provider written as "Chess provider -- Technique used" '''
        pass

    def assign_game(self, url):
        ''' (Abstract) Detect the unique identifier of URL '''
        pass

    def download_game(self):
        ''' (Abstract) Download the game identified earlier by assign_game() '''
        pass


# Lichess.org
class InternetGameLichess(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.url_type = TYPE_NONE
        self.url_tld = 'org'

    def get_description(self):
        return 'Lichess.org -- %s' % CAT_DL

    def assign_game(self, url):
        # Retrieve the ID of the broadcast
        rxp = re.compile(r'^https?:\/\/(\S+\.)?lichess\.(org|dev)\/broadcast\/[a-z0-9\-]+\/([a-z0-9]+)[\/\?\#]?', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            gid = m.group(3)
            if len(gid) == 8:
                self.url_type = TYPE_STUDY
                self.id = gid
                self.url_tld = m.group(2)
                return True

        # Retrieve the ID of the practice
        rxp = re.compile(r'^https?:\/\/(\S+\.)?lichess\.(org|dev)\/practice\/[\w\-\/]+\/([a-z0-9]+\/[a-z0-9]+)(\.pgn)?\/?([\S\/]+)?$', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            gid = m.group(3)
            if len(gid) == 17:
                self.url_type = TYPE_STUDY
                self.id = gid
                self.url_tld = m.group(2)
                return True

        # Retrieve the ID of the study
        rxp = re.compile(r'^https?:\/\/(\S+\.)?lichess\.(org|dev)\/study\/([a-z0-9]+(\/[a-z0-9]+)?)(\.pgn)?\/?([\S\/]+)?$', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            gid = m.group(3)
            if len(gid) in [8, 17]:
                self.url_type = TYPE_STUDY
                self.id = gid
                self.url_tld = m.group(2)
                return True

        # Retrieve the ID of the puzzle
        rxp = re.compile(r'^https?:\/\/(\S+\.)?lichess\.(org|dev)\/training\/([0-9]+|daily)[\/\?\#]?', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            gid = m.group(3)
            if (gid.isdigit() and gid != '0') or gid == 'daily':
                self.url_type = TYPE_PUZZLE
                self.id = gid
                self.url_tld = m.group(2)
                return True

        # Retrieve the ID of the game
        rxp = re.compile(r'^https?:\/\/(\S+\.)?lichess\.(org|dev)\/(game\/export\/|embed\/)?([a-z0-9]+)\/?([\S\/]+)?$', re.IGNORECASE)  # More permissive
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

    def query_api(self, path):
        response = urlopen(Request('https://lichess.%s%s' % (self.url_tld, path), headers={'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/vnd.lichess.v4+json'}))
        bourne = self.read_data(response)
        return self.json_loads(bourne)

    def download_game(self):
        # Check
        if None in [self.id, self.url_tld]:
            return None

        # Logic for the games
        if self.url_type == TYPE_GAME:
            # Download the finished game
            api = self.query_api('/import/master/%s/white' % self.id)
            game = self.json_field(api, 'game')
            if 'winner' in game:
                url = 'https://lichess.%s/game/export/%s?literate=1' % (self.url_tld, self.id)
                return self.download(url)
            else:
                if not self.allow_extra and game['rated']:
                    return None

            # Rebuild the PGN file
            game = {}
            game['_url'] = 'https://lichess.%s%s' % (self.url_tld, self.json_field(api, 'url/round'))
            game['Variant'] = self.json_field(api, 'game/variant/name')
            game['FEN'] = self.json_field(api, 'game/initialFen')
            game['SetUp'] = '1'
            game['White'] = self.json_field(api, 'player/name', self.json_field(api, 'player/user/username', 'Anonymous'))
            game['WhiteElo'] = self.json_field(api, 'player/rating')
            game['Black'] = self.json_field(api, 'opponent/name', self.json_field(api, 'opponent/user/username', 'Anonymous'))
            game['BlackElo'] = self.json_field(api, 'opponent/rating')
            if self.json_field(api, 'clock') != '':
                game['TimeControl'] = '%d+%d' % (self.json_field(api, 'clock/initial'), self.json_field(api, 'clock/increment'))
            else:
                game['TimeControl'] = '%dd' % (self.json_field(api, 'correspondence/increment') // 86400)
            game['Result'] = '*'
            game['_moves'] = ''
            moves = self.json_field(api, 'steps')
            for move in moves:
                if move['ply'] > 0:
                    game['_moves'] += ' %s' % move['san']
            return self.rebuild_pgn(game)

        # Logic for the studies
        elif self.url_type == TYPE_STUDY:
            url = 'https://lichess.%s/study/%s.pgn' % (self.url_tld, self.id)
            return self.download(url, userAgent=True)

        # Logic for the puzzles
        elif self.url_type == TYPE_PUZZLE:
            # The API doesn't provide the history of the moves
            # chessgame = self.query_api('/training/%s/load' % self.id)

            # Fetch the puzzle
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
            game['_url'] = 'https://lichess.%s/%s#%s' % (self.url_tld, self.json_field(puzzle, 'gameId'), self.json_field(puzzle, 'initialPly'))
            game['Site'] = 'lichess.%s' % self.url_tld
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
            assert(False)


# ChessGames.com
class InternetGameChessgames(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.computer = False

    def get_description(self):
        return 'ChessGames.com -- %s' % CAT_DL

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
        return 'FicsGames.org -- %s' % CAT_DL

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
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.url_type = None

    def get_description(self):
        return 'ChessTempo.com -- %s' % CAT_WS

    def assign_game(self, url):
        # Puzzles
        rxp = re.compile(r'^https?:\/\/(\S+\.)?chesstempo\.com\/chess-tactics\/(\d+)', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            gid = str(m.group(2))
            if gid.isdigit() and gid != '0':
                self.id = gid
                self.url_type = TYPE_PUZZLE
                return True

        # Games
        rxp = re.compile(r'^https?:\/\/(\S+\.)?chesstempo\.com\/gamedb\/game\/(\d+)', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            gid = str(m.group(2))
            if gid.isdigit() and gid != '0':
                self.id = gid
                self.url_type = TYPE_GAME
                return True
        return False

    def download_game(self):
        # Check
        if None in [self.id, self.url_type]:
            return None

        # Games
        if self.url_type == TYPE_GAME:
            pgn = self.download('http://chesstempo.com/requests/download_game_pgn.php?gameids=%s' % self.id, userAgent=True)  # Else a random game is retrieved
            if pgn is None or len(pgn) <= 128:
                return None
            else:
                return pgn

        # Puzzles
        elif self.url_type == TYPE_PUZZLE:

            # Open a websocket to retrieve the puzzle
            @asyncio.coroutine
            def coro():
                result = None
                ws = yield from websockets.connect('wss://chesstempo.com:443/ws', origin="https://chesstempo.com", extra_headers=[('User-agent', self.userAgent)], ping_interval=None)
                try:
                    # Check the welcome message
                    data = yield from ws.recv()
                    data = self.json_loads(data)
                    if (data['eventName'] == 'connectionStarted') and (data['data'] == 'started'):

                        # Call the puzzle
                        yield from ws.send('{"eventName":"get-problem-session-data","data":{"problemSetId":1,"sessionSize":20}}')
                        yield from ws.send('{"eventName":"set-problem-difficulty","data":{"difficulty":"","problemSetId":1}}')
                        yield from ws.send('{"eventName":"get-tactic","data":{"problemId":%s,"vo":false}}' % self.id)

                        for i in range(3):
                            data = yield from ws.recv()
                            data = self.json_loads(data)
                            if data['eventName'] == 'get-tactic-result':
                                if data['enc']:
                                    data = ''.join(map(lambda v: v if v < '0' or v > '9' else str((9 + int(v)) % 10), list(data['data'])))
                                    result = b64decode(data).decode().strip()
                                else:
                                    result = data['data'].strip()
                finally:
                    yield from ws.close()
                return result

            data = self.async_from_sync(coro())
            if data in [None, '']:
                return None

            # Rebuild the puzzle
            puzzle = self.json_loads(data)
            game = {}
            game['_url'] = 'https://chesstempo.com/chess-tactics/%s' % self.id
            game['Event'] = 'Puzzle %s' % self.json_field(puzzle, 'tacticInfo/problem_id')
            game['White'] = _('White')
            game['Black'] = _('Black')
            game['Result'] = '*'
            game['FEN'] = self.json_field(puzzle, 'tacticInfo/startPosition')
            game['SetUp'] = '1'
            game['_moves'] = '{%s} %s' % (self.json_field(puzzle, 'tacticInfo/prevmove'), self.json_field(puzzle, 'tacticInfo/moves'))
            return self.rebuild_pgn(game)

        return None


# Chess24.com
class InternetGameChess24(InternetGameInterface):
    def get_description(self):
        return 'Chess24.com -- %s' % CAT_HTML

    def assign_game(self, url):
        rxp = re.compile(r'^https?:\/\/chess24\.com\/[a-z]+\/(analysis|game|download-game)\/([a-z0-9\-_]+)[\/\?\#]?', re.IGNORECASE)
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
                    game['Variant'] = CHESS960
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
        return '365chess.com -- %s' % CAT_HTML

    def assign_game(self, url):
        # Verify the URL
        parsed = urlparse(url)
        if parsed.netloc.lower() not in ['www.365chess.com', '365chess.com']:
            return False
        ppl = parsed.path.lower()
        if ppl == '/game.php':
            key = 'gid'
        elif ppl == '/view_game.php':
            key = 'g'
        else:
            return False

        # Read the arguments
        args = parse_qs(parsed.query)
        if key in args:
            gid = args[key][0]
            if gid.isdigit() and gid != '0':
                self.id = gid
                return True
        return False

    def download_game(self):
        # Download
        if self.id is None:
            return None
        url = 'https://www.365chess.com/game.php?gid=%s' % self.id
        page = self.download(url)
        if page is None:
            return None

        # Played moves
        game = {}
        pos1 = page.find("chess_game.Init({")
        pos1 = page.find(",pgn:'", pos1)
        pos2 = page.find("'", pos1 + 6)
        if -1 in [pos1, pos2]:
            return None
        game['_moves'] = page[pos1 + 6:pos2]

        # Result
        result = game['_moves'].split(' ')[-1]
        if result in reprResult:
            game['Result'] = result
            game['_moves'] = " ".join(game['_moves'].split(' ')[0:-1])

        # Header
        game['_url'] = url
        lines = page.replace("<td", "\n<td").split("\n")
        rxp = re.compile(r'^([\w\-,\s]+)(\(([0-9]+)\))? vs\. ([\w\-,\s]+)(\(([0-9]+)\))?$', re.IGNORECASE)
        game['White'] = _('Unknown')
        game['Black'] = _('Unknown')
        for line in lines:
            line = line.strip()

            # Event
            for tag in ['Event', 'Site', 'Date', 'Round']:
                if tag + ':' in line:
                    pos1 = line.find(tag + ':')
                    pos1 = line.find(' ', pos1)
                    pos2 = line.find('<', pos1)
                    if -1 not in [pos1, pos2]:
                        v = line[pos1 + 1:pos2]
                        if tag == 'Date':
                            v = '%s.%s.%s' % (v[-4:], v[:2], v[3:5])  # mm/dd/yyyy --> yyyy.mm.dd
                        game[tag] = v

            # Players
            line = self.stripHtml(line).strip()
            m = rxp.match(line)
            if m is not None:
                game['White'] = str(m.group(1)).strip()
                if m.group(3) is not None:
                    game['WhiteElo'] = str(m.group(3)).strip()
                game['Black'] = str(m.group(4)).strip()
                if m.group(6) is not None:
                    game['BlackElo'] = str(m.group(6)).strip()

        # Rebuild the PGN game
        return self.rebuild_pgn(game)


# ChessPastebin.com
class InternetGameChesspastebin(InternetGameInterface):
    def get_description(self):
        return 'ChessPastebin.com -- %s' % CAT_HTML

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
        rxp = re.compile(r'.*?\<div id=\"([0-9]+)_board\"\>\<\/div\>.*?', flags=re.IGNORECASE)
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
        return 'ChessBomb.com -- %s' % CAT_HTML

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
                            bourne = b64decode(data[pos1 + 1:pos2]).decode().strip()
                            self.json = json.loads(bourne)
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
        return 'TheChessWorld.com -- %s' % CAT_DL

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
            rxp = re.compile(r".*pgn_uri:.*'([^']+)'.*", re.IGNORECASE)
            lines = data.split("\n")
            for line in lines:
                m = rxp.match(line)
                if m is not None:
                    links.append('https://www.thechessworld.com' + m.group(1))

        # Collect the games
        return self.download_list(links)


# Chess.org
class InternetGameChessOrg(InternetGameInterface):
    def get_description(self):
        return 'Chess.org -- %s' % CAT_WS

    def assign_game(self, url):
        rxp = re.compile(r'^https?:\/\/chess\.org\/play\/([a-f0-9\-]+)[\/\?\#]?', re.IGNORECASE)
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
        rndI = randint(1, 1000)
        rndS = ''.join(choice(string.ascii_lowercase) for i in range(8))

        # Open a websocket to retrieve the chess data
        @asyncio.coroutine
        def coro():
            url = 'wss://chess.org:443/play-sockjs/%d/%s/websocket' % (rndI, rndS)
            log.debug('Websocket connecting to %s' % url)
            ws = yield from websockets.connect(url, origin="https://chess.org:443", ping_interval=None)
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
            game['Variant'] = CHESS960
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
        resultTable = [(0, '*', 'Game started'),                 # ALIVE
                       (1, '1-0', 'White checkmated'),           # WHITE_MATE
                       (2, '0-1', 'Black checkmated'),           # BLACK_MATE
                       (3, '1/2-1/2', 'White stalemated'),       # WHITE_STALEMATE
                       (4, '1/2-1/2', 'Black stalemated'),       # BLACK_STALEMATE
                       (5, '1/2-1/2', 'Insufficient material'),  # DRAW_NO_MATE
                       (6, '1/2-1/2', '50-move rule'),           # DRAW_50
                       (7, '1/2-1/2', 'Threefold repetition'),   # DRAW_REP
                       (8, '1/2-1/2', 'Mutual agreement'),       # DRAW_AGREE
                       (9, '0-1', 'White resigned'),             # WHITE_RESIGN
                       (10, '1-0', 'Black resigned'),            # BLACK_RESIGN
                       (11, '0-1', 'White canceled'),            # WHITE_CANCEL
                       (12, '1-0', 'Black canceled'),            # BLACK_CANCEL
                       (13, '1-0', 'White out of time'),         # WHITE_NO_TIME
                       (14, '0-1', 'Black out of time'),         # BLACK_NO_TIME
                       (15, '*', 'Not started')]                 # NOT_STARTED
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
        return 'Europe-Echecs.com -- %s' % CAT_DL

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
            rxp = re.compile(r".*class=\"cbwidget\"\s+id=\"([0-9a-f]+)_container\".*", re.IGNORECASE)
            lines = page.split("\n")
            for line in lines:
                m = rxp.match(line)
                if m is not None:
                    links.append('https://www.europe-echecs.com/embed/doc_%s.pgn' % m.group(1))

        # Collect the games
        return self.download_list(links)


# GameKnot.com
class InternetGameGameknot(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.url_type = TYPE_NONE

    def get_description(self):
        return 'GameKnot.com -- %s' % CAT_HTML

    def assign_game(self, url):
        # Verify the hostname
        parsed = urlparse(url.lower())
        if parsed.netloc not in ['www.gameknot.com', 'gameknot.com']:
            return False

        # Verify the page
        if parsed.path == '/analyze-board.pl':
            ttype = TYPE_GAME
            tkey = 'bd'
        elif parsed.path == '/chess-puzzle.pl':
            ttype = TYPE_PUZZLE
            tkey = 'pz'
        else:
            return False

        # Read the arguments
        args = parse_qs(parsed.query)
        if tkey in args:
            gid = args[tkey][0]
            if gid.isdigit() and gid != '0':
                self.id = gid
                self.url_type = ttype
                return True
        return False

    def download_game(self):
        # Check
        if self.url_type not in [TYPE_GAME, TYPE_PUZZLE] or self.id is None:
            return None

        # Download
        if self.url_type == TYPE_GAME:
            url = 'https://gameknot.com/analyze-board.pl?bd=%s' % self.id
        elif self.url_type == TYPE_PUZZLE:
            url = 'https://gameknot.com/chess-puzzle.pl?pz=%s' % self.id
        else:
            assert(False)
        page = self.download(url, userAgent=True)
        if page is None:
            return None

        # Library
        def extract_variables(page, structure):
            game = {}
            for var, type, tag in structure:
                game[tag] = ''
            lines = page.split(';')
            for line in lines:
                for var, type, tag in structure:
                    pos1 = line.find(var)
                    if pos1 == -1:
                        continue
                    if type == 's':
                        pos1 = line.find("'", pos1 + 1)
                        pos2 = line.find("'", pos1 + 1)
                        if pos2 > pos1:
                            game[tag] = line[pos1 + 1:pos2]
                    elif type == 'i':
                        pos1 = line.find('=', pos1 + 1)
                        if pos1 != -1:
                            txt = line[pos1 + 1:].strip()
                            if txt not in ['', '0']:
                                game[tag] = txt
                    else:
                        assert(False)
            return game

        # Logic for the puzzles
        if self.url_type == TYPE_PUZZLE:
            structure = [('puzzle_id', 'i', '_id'),
                         ('puzzle_fen', 's', 'FEN'),
                         ('load_solution(', 's', '_solution')]
            game = extract_variables(page, structure)
            game['_url'] = 'https://gameknot.com/chess-puzzle.pl?pz=%s' % game['_id']
            game['White'] = _('White')
            game['Black'] = _('Black')
            game['Result'] = '*'
            if game['FEN'] != '':
                game['SetUp'] = '1'
            if game['_solution'] != '':
                list = game['_solution'].split('|')
                game['_moves'] = ' {Solution:'
                nextid = '0'
                for item in list:
                    item = item.split(',')
                    # 0 = identifier of the move
                    # 1 = player
                    # 2 = identifier of the previous move
                    # 3 = count of following moves
                    # 4 = algebraic notation of the move
                    # 5 = UCI notation of the move
                    # 6 = ?
                    # 7 = identifier of the next move
                    # > = additional moves for the current line
                    curid = item[0]
                    if curid != nextid:
                        continue
                    if len(item) == 4:
                        break
                    nextid = item[7]
                    if self.use_an:
                        move = item[4]
                    else:
                        move = item[5]
                    game['_moves'] += ' %s' % move
                game['_moves'] += '}'

        # Logic for the games
        elif self.url_type == TYPE_GAME:
            # Header
            structure = [('anbd_movelist', 's', '_moves'),
                         ('anbd_result', 'i', 'Result'),
                         ('anbd_player_w', 's', 'White'),
                         ('anbd_player_b', 's', 'Black'),
                         ('anbd_rating_w', 'i', 'WhiteElo'),
                         ('anbd_rating_b', 'i', 'BlackElo'),
                         ('anbd_title', 's', 'Event'),
                         ('anbd_timestamp', 's', 'Date'),
                         ('export_web_input_result_text', 's', '_reason')]
            game = extract_variables(page, structure)
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
            board.applyFen(DEFAULT_BOARD)
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
        return unquote(self.rebuild_pgn(game))


# Chess.com
class InternetGameChessCom(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.url_type = None

    def get_description(self):
        return 'Chess.com -- %s' % CAT_HTML

    def assign_game(self, url):
        # Positions
        parsed = urlparse(url)
        if parsed.netloc.lower() in ['www.chess.com', 'chess.com']:
            args = parse_qs(parsed.query)
            if 'fen' in args:
                fen = args['fen'][0]
                if self.isFen(fen):
                    self.url_type = TYPE_FEN
                    self.id = fen
                    return True

        # Puzzles
        rxp = re.compile(r'^https?:\/\/(\S+\.)?chess\.com\/([a-z\/]+)?(puzzles)\/problem\/([0-9]+)[\/\?\#]?', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            self.url_type = m.group(3)
            self.id = m.group(4)
            return True

        # Games
        rxp = re.compile(r'^https?:\/\/(\S+\.)?chess\.com\/([a-z\/]+)?(live|daily)\/([a-z\/]+)?([0-9]+)[\/\?\#]?', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            self.url_type = m.group(3)
            self.id = m.group(5)
            return True
        return False

    def decode_move(self, move):
        # Mapping
        map = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!?{~}(^)[_]@#$,./&-*++='
        pieces = 'qnrbkp'

        # Analyze the move
        sFrom = sTo = sPromo = sDrop = ''
        posFrom = map.index(move[:1])
        posTo = map.index(move[1:])
        if posTo > 63:
            sPromo = pieces[(posTo - 64) // 3]
            posTo = posFrom + (-8 if posFrom < 16 else 8) + (posTo - 1) % 3 - 1
        if posFrom > 75:
            sDrop = pieces[posFrom - 79].upper() + '@'
        else:
            sFrom = map[posFrom % 8] + str((posFrom // 8 + 1))
        sTo = map[posTo % 8] + str((posTo // 8 + 1))
        return '%s%s%s%s' % (sDrop, sFrom, sTo, sPromo)

    def download_game(self):
        # Check
        if None in [self.id, self.url_type]:
            return None

        # Positions
        if self.url_type == TYPE_FEN:
            return '[Site "chess.com"]\n[White "%s"]\n[Black "%s"]\n[SetUp "1"]\n[FEN "%s"]\n\n*' % (_('White'), _('Black'), self.id)

        # Puzzles
        elif self.url_type == 'puzzles':
            url = 'https://www.chess.com/puzzles/problem/%s' % self.id
            page = self.download(url, userAgent=True)  # Else 403 Forbidden
            if page is None:
                return None

            # Definition of the parser
            class chesscomparser(HTMLParser):
                def __init__(self):
                    HTMLParser.__init__(self)
                    self.pgn = None

                def handle_starttag(self, tag, attrs):
                    if tag.lower() == 'div':
                        for k, v in attrs:
                            if k.lower() == 'data-puzzle':
                                self.pgn = v.replace('&quote;', '"').replace('\\/', '/')

            # Parse the page
            parser = chesscomparser()
            parser.feed(page)
            if parser.pgn is None:
                return None

            # Load the JSON
            puzzle = self.json_loads(parser.pgn)
            if puzzle in [None, '']:
                return None

            # Get the game directly if available
            pgn = self.json_field('puzzle', 'pgn')
            if pgn != '':
                pgn = pgn.replace('\\n', '\n')
                pgn = pgn.replace('\\"', '"')
                pgn = pgn.replace('     ', ' ')
                pgn = pgn.replace('. ...', '...')
                pgn = pgn.replace('\\t', '    ')
                return pgn

            # Rebuild the puzzle
            game = {}
            game['_url'] = url
            refid = self.json_field('puzzle', 'gameLiveId')
            if refid not in [None, 0, '']:
                game['_url'] = 'https://www.chess.com/live/game/%d' % refid
            else:
                refid = self.json_field('puzzle', 'gameId')
                if refid not in [None, 0, '']:
                    game['_url'] = 'https://www.chess.com/daily/game/%d' % refid
            rating = self.json_field(puzzle, 'rating')
            game['Event'] = 'Puzzle %s, rated %s' % (str(self.json_field(puzzle, 'id')), rating)
            game['White'] = _('White')
            game['Black'] = _('Black')
            game['Result'] = '*'
            game['TimeControl'] = '%d+0' % self.json_field(puzzle, 'averageSeconds')
            game['FEN'] = self.json_field(puzzle, 'initialFen')
            game['SetUp'] = '1'
            game['X_ID'] = self.json_field(puzzle, 'id')
            game['X_Rating'] = rating
            game['X_Attempts'] = self.json_field(puzzle, 'attemptCount')
            game['X_PassRate'] = self.json_field(puzzle, 'passRate')
            buffer = self.json_field(puzzle, 'internalNote').strip()
            if buffer == '':
                buffer = '{%s}' % _('The first move is not provided')
            game['_moves'] = buffer

        # Games
        else:
            # Download
            url = 'https://www.chess.com/%s/game/%s' % (self.url_type, self.id)
            page = self.download(url, userAgent=True)  # Else 403 Forbidden
            if page is None:
                return None

            # Extract the JSON
            bourne = ''
            pos1 = page.find('window.chesscom.dailyGame')
            if pos1 != -1:
                pos1 = page.find('(', pos1)
                pos2 = page.find(')', pos1 + 1)
                if pos2 > pos1:
                    bourne = page[pos1 + 2:pos2 - 1].replace('\\\\\\/', '/').replace('\\"', '"')
            if bourne == '':
                return None
            chessgame = self.json_loads(bourne)
            if not self.allow_extra and self.json_field(chessgame, 'game/isRated') and not self.json_field(chessgame, 'game/isFinished'):
                return None
            chessgame = self.json_field(chessgame, 'game')
            if chessgame == '':
                return None

            # Header
            headers = self.json_field(chessgame, 'pgnHeaders')
            if headers == '':
                game = {}
            else:
                game = headers
            if 'Variant' in game and game['Variant'] == 'Chess960':
                game['Variant'] = CHESS960
            game['_url'] = url

            # Body
            moves = self.json_field(chessgame, 'moveList')
            if moves == '':
                return None
            game['_moves'] = ''
            if 'Variant' in game and game['Variant'] == 'Crazyhouse':
                board = LBoard(variant=CRAZYHOUSECHESS)
            else:
                board = LBoard(variant=FISCHERRANDOMCHESS)
            if 'FEN' in game:
                board.applyFen(game['FEN'])
            else:
                board.applyFen(DEFAULT_BOARD)
            while len(moves) > 0:
                move = self.decode_move(moves[:2])
                moves = moves[2:]
                try:
                    if self.use_an:
                        kmove = parseAny(board, move)
                        game['_moves'] += toSAN(board, kmove) + ' '
                        board.applyMove(kmove)
                    else:
                        game['_moves'] += move + ' '
                except Exception:
                    return None

        # Final PGN
        return self.rebuild_pgn(game)


# Schach-Spielen.eu
class InternetGameSchachspielen(InternetGameInterface):
    def get_description(self):
        return 'Schach-Spielen.eu -- %s' % CAT_HTML

    def assign_game(self, url):
        rxp = re.compile(r'^https?:\/\/(www\.)?schach-spielen\.eu\/(game|analyse)\/([a-z0-9]+)[\/\?\#]?', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            gid = m.group(3)
            if len(gid) == 8:
                self.id = gid
                return True
        return False

    def download_game(self):
        # Download
        if self.id is None:
            return None
        page = self.download('https://www.schach-spielen.eu/analyse/%s' % self.id)
        if page is None:
            return None

        # Definition of the parser
        class schachspielenparser(HTMLParser):
            def __init__(self):
                HTMLParser.__init__(self)
                self.tag_ok = False
                self.pgn = None

            def handle_starttag(self, tag, attrs):
                if tag.lower() == 'textarea':
                    for k, v in attrs:
                        if k.lower() == 'id' and v == 'pgnText':
                            self.tag_ok = True

            def handle_data(self, data):
                if self.pgn is None and self.tag_ok:
                    self.pgn = data

        # Read the PGN
        parser = schachspielenparser()
        parser.feed(page)
        pgn = parser.pgn
        if pgn is not None:
            pgn = pgn.replace('[Variant "chess960"]', '[Variant "%s"]' % CHESS960)
        return pgn


# RedHotPawn.com
class InternetGameRedhotpawn(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.url_type = None

    def get_description(self):
        return 'RedHotPawn.com -- %s' % CAT_HTML

    def assign_game(self, url):
        # Verify the URL
        parsed = urlparse(url)
        if parsed.netloc.lower() not in ['www.redhotpawn.com', 'redhotpawn.com']:
            return False

        # Verify the path
        ppl = parsed.path.lower()
        if 'chess-game-' in ppl:
            ttype = TYPE_GAME
            key = 'gameid'
        elif 'chess-puzzle-' in ppl:
            ttype = TYPE_PUZZLE
            if 'chess-puzzle-serve' in url.lower():
                self.url_type = ttype
                self.id = url
                return True
            else:
                key = 'puzzleid'
        else:
            return False

        # Read the arguments
        args = parse_qs(parsed.query)
        if key in args:
            gid = args[key][0]
            if gid.isdigit() and gid != '0':
                self.url_type = ttype
                self.id = gid
                return True
        return False

    def download_game(self):
        # Download
        if self.id is None:
            return None
        if self.url_type == TYPE_GAME:
            url = 'https://www.redhotpawn.com/pagelet/view/game-pgn.php?gameid=%s' % self.id
        elif self.url_type == TYPE_PUZZLE:
            if '://' in self.id:
                url = self.id
                event = _('Puzzle')
            else:
                url = 'https://www.redhotpawn.com/chess-puzzles/chess-puzzle-solve.php?puzzleid=%s' % self.id
                event = _('Puzzle %s') % self.id
        else:
            return None
        page = self.download(url)
        if page is None:
            return None

        # Logic for the games
        if self.url_type == TYPE_GAME:
            # Parser
            class redhotpawnparser(HTMLParser):
                def __init__(self):
                    HTMLParser.__init__(self)
                    self.tag_ok = False
                    self.pgn = None

                def handle_starttag(self, tag, attrs):
                    if tag.lower() == 'textarea':
                        self.tag_ok = True

                def handle_data(self, data):
                    if self.pgn is None and self.tag_ok:
                        self.pgn = data

            # Extractor
            parser = redhotpawnparser()
            parser.feed(page)
            return parser.pgn.strip()

        # Logic for the puzzles
        elif self.url_type == TYPE_PUZZLE:
            pos1 = page.find('var g_startFenStr')
            if pos1 != -1:
                pos1 = page.find("'", pos1)
                pos2 = page.find("'", pos1 + 1)
                if pos2 > pos1:
                    game = {}
                    game['_url'] = url
                    game['FEN'] = page[pos1 + 1:pos2]
                    game['SetUp'] = '1'
                    game['Event'] = event
                    game['White'] = _('White')
                    game['Black'] = _('Black')
                    pos1 = page.find('<h4>')
                    pos2 = page.find('</h4>', pos1)
                    if pos1 != -1 and pos2 > pos1:
                        game['_moves'] = '{%s}' % page[pos1 + 4:pos2]
                    return self.rebuild_pgn(game)

        return None


# Chess-Samara.ru
class InternetGameChesssamara(InternetGameInterface):
    def get_description(self):
        return 'Chess-Samara.ru -- %s' % CAT_DL

    def assign_game(self, url):
        rxp = re.compile(r'^https?:\/\/(\S+\.)?chess-samara\.ru\/(\d+)\-', re.IGNORECASE)
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
        pgn = self.download('https://chess-samara.ru/view/pgn.html?gameid=%s' % self.id)
        if pgn is None or len(pgn) == 0:
            return None
        else:
            return pgn


# 2700chess.com
class InternetGame2700chess(InternetGameInterface):
    def get_description(self):
        return '2700chess.com -- %s' % CAT_HTML

    def assign_game(self, url):
        # Verify the hostname
        parsed = urlparse(url)
        if parsed.netloc.lower() not in ['www.2700chess.com', '2700chess.com']:
            return False

        # Refactor the direct link
        if parsed.path.lower() == '/games/download':
            args = parse_qs(parsed.query)
            if 'slug' in args:
                self.id = 'https://2700chess.com/games/%s' % args['slug'][0]
                return True

        # Verify the path
        if parsed.path.startswith('/games/'):
            self.id = url
            return True
        else:
            return False

    def download_game(self):
        # Download
        if self.id is None:
            return None
        page = self.download(self.id)
        if page is None:
            return None

        # Extract the PGN
        lines = page.split(';')
        for line in lines:
            if 'analysis.setPgn(' in line:
                pos1 = line.find('"')
                if pos1 != -1:
                    pos2 = pos1
                    while pos2 < len(line):
                        pos2 += 1
                        if line[pos2] == '"' and line[pos2 - 1:pos2 + 1] != '\\"':
                            pgn = line[pos1 + 1:pos2]
                            return pgn.replace('\\"', '"').replace('\\/', '/').replace('\\n', "\n").strip()
        return None


# Iccf.com
class InternetGameIccf(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.url_type = None

    def get_description(self):
        return 'Iccf.com -- %s' % CAT_DL

    def assign_game(self, url):
        # Verify the hostname
        parsed = urlparse(url)
        if parsed.netloc.lower() not in ['www.iccf.com', 'iccf.com']:
            return False

        # Verify the path
        ppl = parsed.path.lower()
        if '/game' in ppl:
            ttyp = TYPE_GAME
        elif '/event' in ppl:
            ttyp = TYPE_EVENT
        else:
            return False

        # Read the arguments
        args = parse_qs(parsed.query)
        if 'id' in args:
            gid = args['id'][0]
            if gid.isdigit() and gid != '0':
                self.url_type = ttyp
                self.id = gid
                return True
        return False

    def download_game(self):
        # Check
        if self.url_type not in [TYPE_GAME, TYPE_EVENT] or self.id is None:
            return None

        # Download
        if self.url_type == TYPE_GAME:
            url = 'https://www.iccf.com/GetPGN.aspx?id=%s'
        elif self.url_type == TYPE_EVENT:
            url = 'https://www.iccf.com/GetEventPGN.aspx?id=%s'
        pgn = self.download(url % self.id)
        if pgn in [None, ''] or 'does not exist.' in pgn or 'Invalid event' in pgn:
            return None
        else:
            return pgn


# SchachArena.de
class InternetGameSchacharena(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)

    def get_description(self):
        return 'SchachArena.de -- %s' % CAT_HTML

    def assign_game(self, url):
        # Verify the URL
        parsed = urlparse(url)
        if parsed.netloc.lower() not in ['www.schacharena.de', 'schacharena.de'] or 'verlauf' not in parsed.path.lower():
            return False

        # Read the arguments
        args = parse_qs(parsed.query)
        if 'brett' in args:
            gid = args['brett'][0]
            if gid.isdigit() and gid != '0':
                self.id = gid
                return True
        return False

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download page
        page = self.download('https://www.schacharena.de/new/verlauf.php?brett=%s' % self.id)
        if page is None:
            return None

        # Init
        rxp_player = re.compile(r'.*spielerstatistik.*name=(\w+).*\[([0-9]+)\].*', re.IGNORECASE)
        rxp_move = re.compile(r'.*<span.*onMouseOut.*fan\(([0-9]+)\).*', re.IGNORECASE)
        rxp_result = re.compile(r'.*>(1\-0|0\-1|1\/2\-1\/2)\s([^\<]+)<.*', re.IGNORECASE)
        player_count = 0
        board = LBoard()
        board.applyFen(DEFAULT_BOARD)

        # Parse
        game = {}
        game['Result'] = '*'
        reason = ''
        game['_moves'] = ''
        game['_url'] = 'https://www.schacharena.de/new/verlauf_to_pgn_n.php?brett=%s' % self.id  # If one want to get the full PGN
        lines = page.split("\n")
        for line in lines:
            # Player
            m = rxp_player.match(line)
            if m is not None:
                player_count += 1
                if player_count == 1:
                    tag = 'White'
                elif player_count == 2:
                    tag = 'Black'
                else:
                    return None
                game[tag] = m.group(1)
                game[tag + 'Elo'] = m.group(2)
                continue

            # Move
            m = rxp_move.match(line)
            if m is not None:
                move = m.group(1)
                move = '_abcdefgh'[int(move[0])] + move[1] + '_abcdefgh'[int(move[2])] + move[3]
                if self.use_an:
                    kmove = parseAny(board, move)
                    move = toSAN(board, kmove)
                    board.applyMove(kmove)
                game['_moves'] += '%s ' % move
                continue

            # Result
            m = rxp_result.match(line)
            if m is not None:
                game['Result'] = m.group(1)
                reason = unescape(m.group(2))
                continue

        # Final PGN
        if reason != '':
            game['_moves'] += ' {%s}' % reason
        return self.rebuild_pgn(game)


# ChessPuzzle.net
class InternetGameChesspuzzle(InternetGameInterface):
    def get_description(self):
        return 'ChessPuzzle.net -- %s' % CAT_HTML

    def assign_game(self, url):
        rxp = re.compile(r'^https?:\/\/(\S+\.)?chesspuzzle\.net\/(Puzzle|Solution)\/([0-9]+)[\/\?\#]?', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            gid = str(m.group(3))
            if gid.isdigit() and gid != '0':
                self.id = gid
                return True
        return False

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download the puzzle
        page = self.download('https://chesspuzzle.net/Solution/%s' % self.id, userAgent=True)  # Else 403 Forbidden
        if page is None:
            return None

        # Definition of the parser
        class chesspuzzleparser(HTMLParser):
            def __init__(self):
                HTMLParser.__init__(self)
                self.last_tag = None
                self.pgn = None

            def handle_starttag(self, tag, attrs):
                self.last_tag = tag.lower()

            def handle_data(self, data):
                if self.pgn is None and self.last_tag == 'script':
                    lines = data.split("\n")
                    for line in lines:
                        pos1 = line.find('pgn_text')
                        if pos1 != -1:
                            pos1 = line.find("'", pos1 + 1)
                            pos2 = line.find("'", pos1 + 1)
                            if pos1 != -1 and pos2 > pos1:
                                self.pgn = line[pos1 + 1:pos2].replace(']  ', "]\n\n").replace('] ', "]\n").strip()
                                break

        # Get the puzzle
        parser = chesspuzzleparser()
        parser.feed(page)
        return parser.pgn


# ChessKing.com
class InternetGameChessking(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.url_type = None

    def get_description(self):
        return 'ChessKing.com -- %s' % CAT_DL

    def assign_game(self, url):
        rxp = re.compile(r'^https?:\/\/(\S+\.)?chessking\.com\/games\/(ff\/)?([0-9]+)[\/\?\#]?', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            gid = str(m.group(3))
            if gid.isdigit() and gid != '0' and len(gid) <= 9:
                if m.group(2) == 'ff/':
                    self.url_type = 'f'
                else:
                    self.url_type = 'g'
                self.id = gid
                return True
        return False

    def download_game(self):
        # Check
        if None in [self.url_type, self.id]:
            return None

        # Download
        id = self.id
        while len(id) < 9:
            id = '0%s' % id
        url = 'https://c1.chessking.com/pgn/%s/%s/%s/%s%s.pgn' % (self.url_type, id[:3], id[3:6], self.url_type, id)
        return self.download(url)


# IdeaChess.com
class InternetGameIdeachess(InternetGameInterface):
    def __init__(self):
        InternetGameInterface.__init__(self)
        self.url_type = None

    def get_description(self):
        return 'IdeaChess.com -- %s' % CAT_API

    def assign_game(self, url):
        # Game ID
        rxp = re.compile(r'^https?:\/\/(\S+\.)?ideachess\.com\/.*\/.*\/([0-9]+)[\/\?\#]?', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            gid = str(m.group(2))
            if gid.isdigit() and gid != '0':
                # Game type
                classification = [('/chess_tactics_puzzles/checkmate_n/', 'm'),
                                  ('/echecs_tactiques/mat_n/', 'm'),
                                  ('/scacchi_tattica/scacco_matto_n/', 'm'),
                                  ('/chess_tactics_puzzles/tactics_n/', 't'),
                                  ('/echecs_tactiques/tactiques_n/', 't'),
                                  ('/scacchi_tattica/tattica_n/', 't')]
                for path, ttyp in classification:
                    if path in url.lower():
                        self.url_type = ttyp
                        self.id = gid
                        return True
        return False

    def download_game(self):
        # Check
        if self.url_type is None or self.id is None:
            return None

        # Fetch the puzzle
        api = 'http://www.ideachess.com/com/ajax2'
        data = {'message': '{"action":100,"data":{"problemNumber":%s,"kind":"%s"}}' % (self.id, self.url_type)}
        bourne = self.send_xhr(api, data, userAgent=True)
        chessgame = self.json_loads(bourne)
        if self.json_field(chessgame, 'action') != 200:
            return None

        # Build the PGN
        game = {}
        if self.url_type == 'm':
            game['_url'] = 'http://www.ideachess.com/chess_tactics_puzzles/checkmate_n/%s' % self.id
        elif self.url_type == 't':
            game['_url'] = 'http://www.ideachess.com/chess_tactics_puzzles/tactics_n/%s' % self.id
        else:
            assert(False)
        game['FEN'] = b64decode(self.json_field(chessgame, 'data/FEN')).decode().strip()
        game['SetUp'] = '1'
        game['_moves'] = self.json_field(chessgame, 'data/PGN')
        v = self.json_field(chessgame, 'data/requiredMoves')
        if v > 0:
            game['Site'] = _('%d moves to find') % v
        list = self.json_field(chessgame, 'data/extraInfo').split('|')
        if len(list) == 4:
            game['Event'] = list[0][list[0].find(' ') + 1:].strip()
            game['Date'] = list[1].strip()
            l2 = list[2].split(' - ')
            if len(l2) == 2:
                game['White'] = l2[0].strip()
                game['Black'] = l2[1].strip()
            game['Result'] = list[3].strip()
        else:
            game['Result'] = '*'
        return self.rebuild_pgn(game)


# Chess-DB.com
class InternetGameChessdb(InternetGameInterface):
    def get_description(self):
        return 'Chess-DB.com -- %s' % CAT_HTML

    def is_enabled(self):
        return False  # Server down

    def assign_game(self, url):
        # Verify the URL
        parsed = urlparse(url)
        if parsed.netloc.lower() not in ['www.chess-db.com', 'chess-db.com'] or 'game.jsp' not in parsed.path.lower():
            return False

        # Read the arguments
        args = parse_qs(parsed.query)
        if 'id' in args:
            gid = args['id'][0]
            rxp = re.compile(r'^[0-9\.]+$', re.IGNORECASE)
            if rxp.match(gid) is not None:
                self.id = gid
                return True
        return False

    def download_game(self):
        # Download
        if self.id is None:
            return None
        page = self.download('https://chess-db.com/public/game.jsp?id=%s' % self.id)
        if page is None:
            return None

        # Definition of the parser
        class chessdbparser(HTMLParser):
            def __init__(self):
                HTMLParser.__init__(self)
                self.tag_ok = False
                self.pgn = None
                self.pgn_tmp = None

            def handle_starttag(self, tag, attrs):
                if tag.lower() == 'input':
                    for k, v in attrs:
                        k = k.lower()
                        if k == 'name' and v == 'pgn':
                            self.tag_ok = True
                        if k == 'value' and v.count('[') == v.count(']'):
                            self.pgn_tmp = v

            def handle_data(self, data):
                if self.pgn is None and self.tag_ok:
                    self.pgn = self.pgn_tmp

        # Read the PGN
        parser = chessdbparser()
        parser.feed(page)
        return parser.pgn


# ChessPro.ru
class InternetGameChesspro(InternetGameInterface):
    def get_description(self):
        return 'ChessPro.ru -- %s' % CAT_HTML

    def assign_game(self, url):
        return self.reacts_to(url, 'chesspro.ru')

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download the page
        page = self.download(self.id)
        if page is None:
            return None

        # Find the chess widget
        rxp = re.compile(r'.*OpenGame\(\s*"g[0-9]+\"\s*,"(.*)"\s*\)\s*;.*', re.IGNORECASE)
        lines = page.split("\n")
        for line in lines:
            m = rxp.match(line)
            if m is not None:
                return '[Annotator "ChessPro.ru"]\n%s' % m.group(1)
        return None


# Ficgs.com
class InternetGameFicgs(InternetGameInterface):
    def get_description(self):
        return 'Ficgs.com -- %s' % CAT_DL

    def assign_game(self, url):
        rxp = re.compile(r'^https?:\/\/(\S+\.)?ficgs\.com\/game_(\d+).html', re.IGNORECASE)
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
        return self.download('http://www.ficgs.com/game_%s.pgn' % self.id)


# Chessbase
class InternetGameChessbase(InternetGameInterface):
    def get_description(self):
        return 'ChessBase.com -- %s' % CAT_HTML

    def assign_game(self, url):
        return self.reacts_to(url, '*')             # Any website can embed a widget from Chessbase

    def download_game(self):
        # Download
        if self.id is None:
            return None
        page = self.download(self.id)
        if page is None:
            return None

        # Definition of the parser
        class chessbaseparser(HTMLParser):
            def __init__(self):
                HTMLParser.__init__(self)
                self.tag_ok = False
                self.links = []
                self.pgn = None

            def handle_starttag(self, tag, attrs):
                # Verify the parent tag
                self.tag_ok = False
                if tag.lower() in ['p', 'div']:
                    for k, v in attrs:
                        if k.lower() == 'class' and v == 'cbreplay':
                            self.tag_ok = True

                    # Content by link
                    if self.tag_ok:
                        for k, v in attrs:
                            if k.lower() == 'data-url':
                                self.links.append(v)

            def handle_data(self, data):
                # Content by data
                if self.tag_ok and self.pgn is None:
                    data = data.strip()
                    if len(data) > 0:       # Empty content if data-url used
                        self.pgn = data

        # Parse the page
        parser = chessbaseparser()
        parser.feed(page)
        if parser.pgn is not None:
            return parser.pgn
        else:
            parser.links = self.expand_links(parser.links, self.id)
            return self.download_list(parser.links)


# PlayOK.com
class InternetGamePlayok(InternetGameInterface):
    def get_description(self):
        return 'PlayOK.com -- %s' % CAT_DL

    def assign_game(self, url):
        # Verify the hostname
        parsed = urlparse(url)
        if parsed.netloc.lower() not in ['www.playok.com', 'playok.com']:
            return False

        # Read the arguments
        args = parse_qs(parsed.query)
        if 'g' in args:
            gid = args['g'][0]
            if gid[:2] == 'ch':
                gid = gid[2:].replace('.txt', '')
                if gid.isdigit() and gid != '0':
                    self.id = gid
                    return True
        return False

    def download_game(self):
        if self.id is not None:
            pgn = self.download('https://www.playok.com/p/?g=ch%s.txt' % self.id)
            if len(pgn) > 16:
                return pgn
        return None


# Pychess.org
class InternetGamePychess(InternetGameInterface):
    def get_description(self):
        return 'Pychess.org -- %s' % CAT_WS

    def assign_game(self, url):
        # Retrieve the ID of the game
        rxp = re.compile(r'https?:\/\/(www\.)?pychess(-variants\.herokuapp\.com|\.org)\/([a-z0-9]+)[\/\?\#]?', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            gid = m.group(3)
            if len(gid) == 8:
                self.id = gid
                return True

        # Nothing found
        return False

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Open a websocket to retrieve the game
        @asyncio.coroutine
        def coro():
            result = None
            ws = yield from websockets.connect('wss://www.pychess.org/wsr', origin="https://www.pychess.org", ping_interval=None)
            try:
                yield from ws.send('{"type":"board","gameId":"%s"}' % self.id)
                for i in range(5):
                    data = yield from ws.recv()
                    data = self.json_loads(data)
                    if data['type'] == 'board' and data['gameId'] == self.id:
                        result = data['pgn']
                        break
            finally:
                yield from ws.close()
            return result

        data = self.async_from_sync(coro())
        return None if data == '' else data


# Generic
class InternetGameGeneric(InternetGameInterface):
    def get_description(self):
        return 'Generic -- %s' % CAT_MISC

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
        if (mime in ['application/x-chess-pgn', 'application/pgn']) or (self.allow_octet_stream and mime == 'application/octet-stream'):
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
            parser.links = self.expand_links(parser.links, self.id)
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
                   InternetGameSchachspielen(),
                   InternetGameRedhotpawn(),
                   InternetGameChesssamara(),
                   InternetGame2700chess(),
                   InternetGameIccf(),
                   InternetGameSchacharena(),
                   InternetGameChesspuzzle(),
                   InternetGameChessking(),
                   InternetGameIdeachess(),
                   InternetGameChessdb(),
                   InternetGameChesspro(),
                   InternetGameFicgs(),
                   InternetGameChessbase(),
                   InternetGamePlayok(),
                   InternetGamePychess(),
                   # TODO ChessDuo.com
                   InternetGameGeneric()]


# Get the list of chess providers
def get_internet_game_providers():
    list = [cp.get_description() for cp in chess_providers]
    list.sort()
    return list


# Retrieve a game from a URL
def get_internet_game_as_pgn(url):
    # Check the format
    if url in [None, '']:
        return None
    p = urlparse(url.strip())
    if '' in [p.scheme, p.netloc]:
        return None
    log.debug('URL to retrieve: %s' % url)

    # Call the chess providers
    for prov in chess_providers:
        if not prov.is_enabled():
            continue
        if prov.assign_game(url):
            # Download
            log.debug('Responding chess provider: %s' % prov.get_description())
            try:
                pgn = prov.download_game()
                pgn = prov.sanitize(pgn)
            except Exception as e:
                pgn = None
                log.debug(str(e))

            # Check
            if pgn is None:
                log.debug('Download failed')
            else:
                log.debug('Successful download')
                return pgn
    return None


# print(get_internet_game_as_pgn(''))

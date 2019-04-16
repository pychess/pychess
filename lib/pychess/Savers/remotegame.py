
import os
import re
import json
from urllib.request import Request, urlopen
from urllib.parse import urlparse, parse_qs
from html.parser import HTMLParser
import base64

from pychess import VERSION
from pychess.Utils.const import FISCHERRANDOMCHESS
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import parseAny, toSAN

# import pdb
# def _(p):
#     return p
# VERSION = '1.0'
# import ssl
# ssl._create_default_https_context = ssl._create_unverified_context


TYPE_NONE, TYPE_GAME, TYPE_STUDY = range(3)


# Abstract class to download a game from the Internet
class InternetGameInterface:
    # Internal
    def __init__(self):
        self.id = None
        self.userAgent = 'PyChess %s' % VERSION

    def get_game_id(self):
        return self.id

    def json_field(self, data, path):
        if data is None:
            return None
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
                    data = ''

        # Result
        return data.replace("\r", '')

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
        # Parse the provided URL to retrieve the ID of the game
        rxp = re.compile('^https?:\/\/([\S]+\.)?lichess\.(org|dev)\/(game\/export\/)?([a-z0-9]+)\/?([\S\/]+)?$', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            id = str(m.group(4))
            if len(id) == 8:
                self.url_type = TYPE_GAME
                self.id = id
                self.url_tld = m.group(2)
                return True

        # Do the same for a study
        rxp = re.compile('^https?:\/\/([\S]+\.)?lichess\.(org|dev)\/study\/([a-z0-9]+(\/[a-z0-9]+)?)(\.pgn)?\/?([\S\/]+)?$', re.IGNORECASE)
        m = rxp.match(url)
        if m is not None:
            id = str(m.group(3))
            if len(id) in [8, 17]:
                self.url_type = TYPE_STUDY
                self.id = id
                self.url_tld = m.group(2)
                return True

        # Nothing found
        return False

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download (possible error 404)
        if self.url_type == TYPE_GAME:
            url = 'https://lichess.%s/game/export/%s?literate=1' % (self.url_tld, self.id)
        elif self.url_type == TYPE_STUDY:
            url = 'https://lichess.%s/study/%s.pgn' % (self.url_tld, self.id)
        else:
            return None
        req = Request(url, headers={'User-Agent': self.userAgent})  # For the studies
        response = urlopen(req)
        return self.read_data(response)


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
        if not parsed.netloc.lower() in ['www.chessgames.com', 'chessgames.com']:
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
            response = urlopen(url + '&comp=1')
            pgn = self.read_data(response)
            if 'NO SUCH GAME' in pgn:
                self.computer = False
            else:
                return pgn

        # Second try without computer analysis
        if not self.computer:
            response = urlopen(url)
            pgn = self.read_data(response)
            if 'NO SUCH GAME' in pgn:
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
        url = 'http://ficsgames.org/cgi-bin/show.cgi?ID=%s;action=save' % self.id
        response = urlopen(url)
        pgn = self.read_data(response)
        if 'not found in GGbID' in pgn:
            return None
        else:
            return pgn


# ChessTempo.com
class InternetGameChesstempo(InternetGameInterface):
    def get_description(self):
        return 'ChessTempo.com -- %s' % _('Download link')

    def assign_game(self, url):
        # Parse the provided URL to retrieve the ID
        rxp = re.compile('^https?:\/\/(\S+\.)?chesstempo\.com\/gamedb\/game\/(\d+)\/?([\S\/]+)?$', re.IGNORECASE)
        m = rxp.match(url)
        if m is None:
            return False

        # Extract the identifier
        gid = str(m.group(2))
        if gid.isdigit() and gid != '0':
            self.id = gid
            return True
        else:
            return False

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download
        url = 'http://chesstempo.com/requests/download_game_pgn.php?gameids=%s' % self.id
        req = Request(url, headers={'User-Agent': self.userAgent})  # Else a random game is retrieved
        response = urlopen(req)
        pgn = self.read_data(response)
        if len(pgn) <= 128:
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
        # Parse the provided URL to retrieve the ID
        rxp = re.compile('^https?:\/\/chess24\.com\/[a-z]+\/(analysis|game|download-game)\/([a-z0-9\-_]+)[\/\?\#]?', re.IGNORECASE)
        m = rxp.match(url)
        if m is None:
            return False

        # Extract the identifier
        gid = str(m.group(2))
        if len(gid) == 22:
            self.id = gid
            return True
        else:
            return False

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download the page
        url = 'https://chess24.com/en/game/%s' % self.id
        req = Request(url, headers={'User-Agent': self.userAgent})  # Else HTTP 403 Forbidden
        response = urlopen(req)
        pgn = self.read_data(response)

        # Extract the JSON of the game
        lines = pgn.split("\n")
        for line in lines:
            line = line.strip()
            pos1 = line.find('.initGameSession({')
            pos2 = line.find('});')
            if -1 in [pos1, pos2]:
                continue

            # Read the game from JSON
            bourne = json.loads(line[pos1 + 17:pos2 + 1])
            game = self.json_field(bourne, 'chessGame')
            moves = self.json_field(game, 'moves')
            if None in [game, moves]:
                continue

            # Build the header of the PGN file
            result = self.json_field(game, 'meta/Result')
            pgn = '[Event "%s"]\n[Site "%s"]\n[Date "%s"]\n[Round "%s"]\n[White "%s"]\n[WhiteElo "%s"]\n[Black "%s"]\n[BlackElo "%s"]\n[Result "%s"]\n' % (
                self.json_field(game, 'meta/Event'),
                self.json_field(game, 'meta/Site'),
                self.json_field(game, 'meta/Date'),
                self.json_field(game, 'meta/Round'),
                self.json_field(game, 'meta/White/Name'),
                self.json_field(game, 'meta/White/Elo'),
                self.json_field(game, 'meta/Black/Name'),
                self.json_field(game, 'meta/Black/Elo'),
                result)

            # Build the PGN
            board = LBoard(variant=FISCHERRANDOMCHESS)
            head_complete = False
            for move in moves:
                # Info from the knot
                kid = self.json_field(move, 'knotId')
                if kid is None:
                    break
                kmove = self.json_field(move, 'move')

                # FEN initialization
                if kid == 0:
                    kfen = self.json_field(move, 'fen')
                    if kfen is None:
                        break
                    kfen = kfen.replace('\/', '/')
                    try:
                        board.applyFen(kfen)
                    except Exception:
                        return None
                    pgn += '[Variant "Fischerandom"]\n[SetUp "1"]\n[FEN "%s"]\n\n{ %s }\n' % (kfen, url)
                    head_complete = True
                else:
                    if not head_complete:
                        return None

                    # Execution of the move
                    if kmove is None:
                        break
                    try:
                        if self.use_an:
                            kmove = parseAny(board, kmove)
                            pgn += toSAN(board, kmove) + ' '
                            board.applyMove(kmove)
                        else:
                            pgn += kmove + ' '
                    except Exception:
                        return None

            # Final result
            pgn += result
            return pgn
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
        # Check
        if self.id is None:
            return None

        # Download
        url = 'https://www.365chess.com/view_game.php?g=%s' % self.id
        response = urlopen(url)
        pgn = self.read_data(response)

        # Played moves
        game = {}
        pos1 = pgn.find(".ApplyPgnMoveText('")
        pos2 = pgn.find("')", pos1)
        if -1 not in [pos1, pos2]:
            game['_pgn'] = pgn[pos1 + 19:pos2]

        # Header
        lines = pgn.split("\n")
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
        pgn = ''
        for e in game:
            if e[:1] != '_':
                pgn += '[%s "%s"]\n' % (e, game[e])
        pgn += '\n%s' % game['_pgn']
        return pgn


# ChessPastebin.com
class InternetGameChesspastebin(InternetGameInterface):
    def get_description(self):
        return 'ChessPastebin.com -- %s' % _('HTML parsing')

    def assign_game(self, url):
        # Verify the hostname
        parsed = urlparse(url)
        if not parsed.netloc.lower() in ['www.chesspastebin.com', 'chesspastebin.com']:
            return False

        # Any page is valid
        self.id = url
        return True

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download
        response = urlopen(self.id)
        pgn = self.read_data(response)

        # Extract the game ID
        rxp = re.compile('.*?\<div id=\"([0-9]+)_board\"\>\<\/div\>.*?', flags=re.IGNORECASE)
        m = rxp.match(pgn.replace("\n", ''))
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
        parser.feed(pgn)
        pgn = parser.pgn
        if pgn is not None:  # Any game should start here with '[' but you can paste anything
            pgn = pgn.strip()
            if not pgn.startswith('['):
                pgn = "[Annotator \"ChessPastebin.com\"]\n%s" % pgn
        return pgn


# ChessBomb.com
class InternetGameChessbomb(InternetGameInterface):
    def get_description(self):
        return 'ChessBomb.com -- %s' % _('HTML parsing')

    def assign_game(self, url):
        # Verify the hostname
        parsed = urlparse(url)
        if not parsed.netloc.lower() in ['www.chessbomb.com', 'chessbomb.com']:
            return False

        # Any page is valid
        self.id = url
        return True

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download
        req = Request(self.id, headers={'User-Agent': self.userAgent})  # Else HTTP 403 Forbidden
        response = urlopen(req)
        pgn = self.read_data(response)

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
        parser.feed(pgn)
        if parser.json is None:
            return None

        # Interpret the JSON
        header = self.json_field(parser.json, 'gameData/game')
        room = self.json_field(parser.json, 'gameData/room')
        moves = self.json_field(parser.json, 'gameData/moves')
        if None in [header, room, moves]:
            return None

        game = {}
        game['Event'] = self.json_field(room, 'name')
        game['Site'] = self.json_field(room, 'officialUrl')
        game['Date'] = self.json_field(header, 'startAt')[:10]
        game['Round'] = self.json_field(header, 'roundSlug')
        game['White'] = self.json_field(header, 'white/name')
        game['WhiteElo'] = self.json_field(header, 'white/elo')
        game['Black'] = self.json_field(header, 'black/name')
        game['BlackElo'] = self.json_field(header, 'black/elo')
        game['Result'] = self.json_field(header, 'result')

        game['_pgn'] = ''
        for move in moves:
            move = self.json_field(move, 'cbn')
            pos1 = move.find('_')
            if pos1 == -1:
                break
            game['_pgn'] += move[pos1 + 1:] + ' '

        # Rebuild the PGN game
        if len(game['_pgn']) == 0:
            return None
        pgn = ''
        for e in game:
            if e[:1] != '_':
                pgn += '[%s "%s"]\n' % (e, game[e])
        pgn += '\n%s%s' % (game['_pgn'], game['Result'])
        return pgn


# Generic
class InternetGameGeneric(InternetGameInterface):
    def get_description(self):
        return 'Generic -- %s' % _('Various techniques')

    def assign_game(self, url):
        self.id = url
        return True

    def download_game(self):
        # Check
        if self.id is None:
            return None

        # Download
        response = urlopen(self.id)
        mime = response.info().get_content_type().lower()
        if mime == 'application/x-chess-pgn':
            return self.read_data(response)
        else:
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
    if '' in [p.scheme, p.netloc, p.path]:
        return None

    # Download a game for each provider
    for prov in chess_providers:
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

            # Extract the first game
            pos = pgn.find("\n\n[")
            if pos != -1:
                pgn = pgn[:pos]

            # Return the PGN with the local crlf
            return pgn.replace("\n", os.linesep)
    return None


# print(get_internet_game_as_pgn(''))

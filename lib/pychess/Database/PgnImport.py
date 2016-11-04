# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import io
import os
import sys
import tempfile
import zipfile
from array import array
from collections import defaultdict

from gi.repository import GLib

from sqlalchemy import bindparam, select, func, and_
from sqlalchemy.exc import SQLAlchemyError

from pychess.compat import unicode, urlopen, HTTPError, URLError
from pychess.Utils.const import NORMALCHESS, FEN_START, reprResult, RUNNING, DRAW, WHITEWON, BLACKWON
from pychess.Utils.lutils.LBoard import START_BOARD
from pychess.Variants import name2variant
# from pychess.System import profile_me
from pychess.System import Timer
from pychess.System.protoopen import protoopen, PGN_ENCODING
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Savers.pgnbase import PgnBase, tagre
from pychess.Savers.database import upd_stat
from pychess.Database.dbwalk import walk
from pychess.Database.model import STAT_PLY_MAX, get_maxint_shift, get_engine, insert_or_ignore,\
    event, site, player, game, annotator, bitboard, tag_game, source, stat


GAME, EVENT, SITE, PLAYER, ANNOTATOR, SOURCE, STAT = range(7)

removeDic = {
    ord(u"'"): None,
    ord(u","): None,
    ord(u"."): None,
    ord(u"-"): None,
    ord(u" "): None,
}

pgn2Const = {"*": RUNNING,
             "?": RUNNING,
             "1/2-1/2": DRAW,
             "1/2": DRAW,
             "1-0": WHITEWON,
             "0-1": BLACKWON}


def download_file(url, progressbar=None):
    temp_file = None
    try:
        if progressbar is not None:
            GLib.idle_add(progressbar.set_text, "Downloading %s ..." % url)
        else:
            print("Downloading %s ..." % url)
        f = urlopen(url)

        temp_file = os.path.join(tempfile.gettempdir(), os.path.basename(url))
        with open(temp_file, "wb") as local_file:
            local_file.write(f.read())

    except HTTPError as e:
        print("HTTP Error:", e.code, url)

    except URLError as e:
        print("URL Error:", e.reason, url)

    return temp_file


class PgnImport():
    def __init__(self, engine):
        self.engine = engine
        self.conn = self.engine.connect()
        self.CHUNK = 1000
        self.cancel = False

        self.count_source = select([func.count()]).select_from(source)

        self.ins_event = event.insert()
        self.ins_site = site.insert()
        self.ins_player = player.insert()
        self.ins_annotator = annotator.insert()
        self.ins_source = source.insert()
        self.ins_game = game.insert()
        self.ins_bitboard = bitboard.insert()
        self.ins_tag_game = tag_game.insert()

        self.ins_stat = insert_or_ignore(engine, stat.insert())
        self.upd_stat = upd_stat

        self.event_dict = {}
        self.site_dict = {}
        self.player_dict = {}
        self.annotator_dict = {}
        self.source_dict = {}

        self.next_id = [0, 0, 0, 0, 0, 0]

        self.next_id[GAME] = self.ini_names(game, GAME)
        self.next_id[EVENT] = self.ini_names(event, EVENT)
        self.next_id[SITE] = self.ini_names(site, SITE)
        self.next_id[PLAYER] = self.ini_names(player, PLAYER)
        self.next_id[ANNOTATOR] = self.ini_names(annotator, ANNOTATOR)
        self.next_id[SOURCE] = self.ini_names(source, SOURCE)

        s = select([player.c.fideid, player.c.id])
        self.fideid_dict = dict([(p[0], p[1]) for p in self.conn.execute(s)])

        self.prefix_stmt = select([player.c.id]).where(player.c.name.startswith(bindparam('name')))

    def get_id(self, name, name_table, field, fide_id=None, info=None):
        if not name:
            return None

        if fide_id is not None and fide_id in self.fideid_dict:
            return self.fideid_dict[fide_id]

        orig_name = name
        if field == EVENT:
            name_dict = self.event_dict
            name_data = self.event_data
        elif field == SITE:
            name_dict = self.site_dict
            name_data = self.site_data
        elif field == ANNOTATOR:
            name_dict = self.annotator_dict
            name_data = self.annotator_data
        elif field == SOURCE:
            name_dict = self.source_dict
            name_data = self.source_data
        elif field == PLAYER:
            name_dict = self.player_dict
            name_data = self.player_data
            name = name.title().translate(removeDic)

        if name in name_dict:
            return name_dict[name]
        elif 0:  # field == PLAYER:
            result = None
            trans = self.conn.begin()
            try:
                result = self.engine.execute(self.prefix_stmt, name=name).first()
                trans.commit()
            except SQLAlchemyError as e:
                trans.rollback()
                print("Importing %s failed! \n%s" % (file, e))
            if result is not None:
                return result[0]

        if field == SOURCE:
            name_data.append({'name': orig_name, 'info': info})
        else:
            name_data.append({'name': orig_name})
        name_dict[name] = self.next_id[field]
        self.next_id[field] += 1
        return name_dict[name]

    def ini_names(self, name_table, field):
        if field != GAME and field != STAT:
            s = select([name_table])
            name_dict = dict([(n.name.title().translate(removeDic), n.id)
                              for n in self.conn.execute(s)])

            if field == EVENT:
                self.event_dict = name_dict
            elif field == SITE:
                self.site_dict = name_dict
            elif field == PLAYER:
                self.player_dict = name_dict
            elif field == ANNOTATOR:
                self.annotator_dict = name_dict
            elif field == SOURCE:
                self.source_dict = name_dict

        s = select([func.max(name_table.c.id).label('maxid')])
        maxid = self.conn.execute(s).scalar()
        if maxid is None:
            next_id = 1
        else:
            next_id = maxid + 1

        return next_id

    def do_cancel(self):
        GLib.idle_add(self.progressbar.set_text, "")
        self.cancel = True

    # @profile_me
    def do_import(self, filename, info=None, progressbar=None):
        DB_MAXINT_SHIFT = get_maxint_shift(self.engine)
        self.progressbar = progressbar

        orig_filename = filename
        count_source = self.conn.execute(self.count_source.where(source.c.name == orig_filename)).scalar()
        if count_source > 0:
            print("%s is already imported" % filename)
            return

        # collect new names not in they dict yet
        self.event_data = []
        self.site_data = []
        self.player_data = []
        self.annotator_data = []
        self.source_data = []

        # collect new games and commit them in big chunks for speed
        self.game_data = []
        self.bitboard_data = []
        self.stat_ins_data = []
        self.stat_upd_data = []
        self.tag_game_data = []

        if filename.startswith("http"):
            filename = download_file(filename, progressbar=progressbar)
            if filename is None:
                return
        else:
            if not os.path.isfile(filename):
                print("Can't open %s" % filename)
                return

        if filename.lower().endswith(".zip") and zipfile.is_zipfile(filename):
            zf = zipfile.ZipFile(filename, "r")
            files = [f for f in zf.namelist() if f.lower().endswith(".pgn")]
        else:
            zf = None
            files = [filename]

        for pgnfile in files:
            basename = os.path.basename(pgnfile)
            if progressbar is not None:
                GLib.idle_add(progressbar.set_text, "Reading %s ..." % basename)
            else:
                print("Reading %s ..." % pgnfile)

            if zf is None:
                size = os.path.getsize(pgnfile)
                handle = protoopen(pgnfile)
            else:
                size = zf.getinfo(pgnfile).file_size
                handle = io.TextIOWrapper(zf.open(pgnfile), encoding=PGN_ENCODING, newline='')

            cf = PgnBase(handle, [])

            # estimated game count
            all_games = max(size / 840, 1)
            self.CHUNK = 1000 if all_games > 5000 else 100

            get_id = self.get_id
            # use transaction to avoid autocommit slowness
            trans = self.conn.begin()
            try:
                i = 0
                for tagtext, movetext in read_games(handle):
                    tags = defaultdict(str, tagre.findall(tagtext))
                    if not tags:
                        print("Empty game #%s" % (i + 1))
                        continue

                    if self.cancel:
                        trans.rollback()
                        return

                    fenstr = tags.get("FEN")

                    variant = tags.get("Variant")
                    if variant:
                        if "fischer" in variant.lower() or "960" in variant:
                            variant = "Fischerandom"
                        else:
                            variant = variant.lower().capitalize()

                    # Fixes for some non statndard Chess960 .pgn
                    if fenstr and variant == "Fischerandom":
                        parts = fenstr.split()
                        parts[0] = parts[0].replace(".", "/").replace("0", "")
                        if len(parts) == 1:
                            parts.append("w")
                            parts.append("-")
                            parts.append("-")
                        fenstr = " ".join(parts)

                    if variant:
                        if variant not in name2variant:
                            print("Unknown variant: %s" % variant)
                            continue
                        variant = name2variant[variant].variant
                        if variant == NORMALCHESS:
                            # lichess uses tag [Variant "Standard"]
                            variant = 0
                            board = START_BOARD.clone()
                        else:
                            board = LBoard(variant)
                    elif fenstr:
                        variant = 0
                        board = LBoard()
                    else:
                        variant = 0
                        board = START_BOARD.clone()

                    if fenstr:
                        try:
                            board.applyFen(fenstr)
                        except SyntaxError as e:
                            print(_(
                                "The game #%s can't be loaded, because of an error parsing FEN")
                                % (i + 1), e.args[0])
                            continue
                    elif variant:
                        board.applyFen(FEN_START)

                    movelist = array("H")
                    comments = []
                    cf.error = None

                    # First we try to use simple_parse_movetext()
                    # assuming most games in .pgn contains only moves
                    # without any comments/variations
                    simple = False
                    if not fenstr and not variant:
                        bitboards = []
                        simple = cf.simple_parse_movetext(movetext, board, movelist, bitboards)

                        if cf.error is not None:
                            print("ERROR in %s game #%s" % (pgnfile, i + 1), cf.error.args[0])
                            continue

                    # If simple_parse_movetext() find any comments/variations
                    # we restart parsing with full featured parse_movetext()
                    if not simple:
                        movelist = array("H")
                        bitboards = None

                        # in case simple_parse_movetext failed we have to reset our lboard
                        if not fenstr and not variant:
                            board = START_BOARD.clone()

                        # parse movetext to create boards tree structure
                        boards = [board]
                        boards = cf.parse_movetext(movetext, boards[0], -1, pgn_import=True)

                        if cf.error is not None:
                            print("ERROR in %s game #%s" % (pgnfile, i + 1), cf.error.args[0])
                            continue

                        # create movelist and comments from boards tree
                        walk(boards[0], movelist, comments)

                    white = tags.get('White')
                    black = tags.get('Black')

                    if not movelist:
                        if (not comments) and (not white) and (not black):
                            print("Empty game #%s" % (i + 1))
                            continue

                    event_id = get_id(tags.get('Event'), event, EVENT)

                    site_id = get_id(tags.get('Site'), site, SITE)

                    game_date = tags.get('Date').strip()
                    try:
                        if game_date and '?' not in game_date:
                            ymd = game_date.split('.')
                            if len(ymd) == 3:
                                game_year, game_month, game_day = map(int, ymd)
                            else:
                                game_year, game_month, game_day = int(game_date[:4]), None, None
                        elif game_date and '?' not in game_date[:4]:
                            game_year, game_month, game_day = int(game_date[:4]), None, None
                        else:
                            game_year, game_month, game_day = None, None, None
                    except:
                        game_year, game_month, game_day = None, None, None

                    game_round = tags.get('Round')

                    white_fide_id = tags.get('WhiteFideId')
                    black_fide_id = tags.get('BlackFideId')

                    white_id = get_id(unicode(white), player, PLAYER, fide_id=white_fide_id)
                    black_id = get_id(unicode(black), player, PLAYER, fide_id=black_fide_id)

                    result = tags.get("Result")
                    if result in pgn2Const:
                        result = pgn2Const[result]
                    else:
                        print("Invalid Result tag in game #%s: %s" % (i + 1, result))
                        continue

                    white_elo = tags.get('WhiteElo')
                    white_elo = int(white_elo) if white_elo and white_elo.isdigit() else None

                    black_elo = tags.get('BlackElo')
                    black_elo = int(black_elo) if black_elo and black_elo.isdigit() else None

                    time_control = tags.get("TimeControl")

                    eco = tags.get("ECO")
                    eco = eco[:3] if eco else None

                    fen = tags.get("FEN")

                    board_tag = tags.get("Board")

                    annotator_id = get_id(tags.get("Annotator"), annotator, ANNOTATOR)

                    source_id = get_id(unicode(orig_filename), source, SOURCE, info=info)

                    game_id = self.next_id[GAME]
                    self.next_id[GAME] += 1

                    # annotated game
                    if bitboards is None:
                        for ply, board in enumerate(boards):
                            if ply == 0:
                                continue
                            bb = board.friends[0] | board.friends[1]
                            # Avoid to include mate in x .pgn collections and similar in opening tree
                            if fen and "/pppppppp/8/8/8/8/PPPPPPPP/" not in fen:
                                ply = -1
                            self.bitboard_data.append({
                                'game_id': game_id,
                                'ply': ply,
                                'bitboard': bb - DB_MAXINT_SHIFT,
                            })

                            if ply <= STAT_PLY_MAX:
                                self.stat_ins_data.append({
                                    'ply': ply,
                                    'bitboard': bb - DB_MAXINT_SHIFT,
                                    'count': 0,
                                    'whitewon': 0,
                                    'blackwon': 0,
                                    'draw': 0,
                                    'white_elo_count': 0,
                                    'black_elo_count': 0,
                                    'white_elo': 0,
                                    'black_elo': 0,
                                })
                                self.stat_upd_data.append({
                                    '_ply': ply,
                                    '_bitboard': bb - DB_MAXINT_SHIFT,
                                    '_count': 1,
                                    '_whitewon': 1 if result == WHITEWON else 0,
                                    '_blackwon': 1 if result == BLACKWON else 0,
                                    '_draw': 1 if result == DRAW else 0,
                                    '_white_elo_count': 1 if white_elo is not None else 0,
                                    '_black_elo_count': 1 if black_elo is not None else 0,
                                    '_white_elo': white_elo if white_elo is not None else 0,
                                    '_black_elo': black_elo if black_elo is not None else 0,
                                })

                    # simple game
                    else:
                        for ply, bb in enumerate(bitboards):
                            if ply == 0:
                                continue
                            self.bitboard_data.append({
                                'game_id': game_id,
                                'ply': ply,
                                'bitboard': bb - DB_MAXINT_SHIFT,
                            })

                            if ply <= STAT_PLY_MAX:
                                self.stat_ins_data.append({
                                    'ply': ply,
                                    'bitboard': bb - DB_MAXINT_SHIFT,
                                    'count': 0,
                                    'whitewon': 0,
                                    'blackwon': 0,
                                    'draw': 0,
                                    'white_elo_count': 0,
                                    'black_elo_count': 0,
                                    'white_elo': 0,
                                    'black_elo': 0,
                                })
                                self.stat_upd_data.append({
                                    '_ply': ply,
                                    '_bitboard': bb - DB_MAXINT_SHIFT,
                                    '_count': 1,
                                    '_whitewon': 1 if result == WHITEWON else 0,
                                    '_blackwon': 1 if result == BLACKWON else 0,
                                    '_draw': 1 if result == DRAW else 0,
                                    '_white_elo_count': 1 if white_elo is not None else 0,
                                    '_black_elo_count': 1 if black_elo is not None else 0,
                                    '_white_elo': white_elo if white_elo is not None else 0,
                                    '_black_elo': black_elo if black_elo is not None else 0,
                                })

                    ply_count = tags.get("PlyCount")
                    if not ply_count and not fen:
                        ply_count = len(bitboards) if bitboards is not None else len(boards)

                    self.game_data.append({
                        'event_id': event_id,
                        'site_id': site_id,
                        'date_year': game_year,
                        'date_month': game_month,
                        'date_day': game_day,
                        'round': game_round,
                        'white_id': white_id,
                        'black_id': black_id,
                        'result': result,
                        'white_elo': white_elo,
                        'black_elo': black_elo,
                        'ply_count': ply_count,
                        'eco': eco,
                        'fen': fen,
                        'variant': variant,
                        'board': board_tag,
                        'time_control': time_control,
                        'annotator_id': annotator_id,
                        'source_id': source_id,
                        'movelist': movelist.tostring(),
                        'comments': unicode("|".join(comments)),
                    })

                    i += 1

                    if len(self.game_data) >= self.CHUNK:
                        if self.event_data:
                            self.conn.execute(self.ins_event, self.event_data)
                            self.event_data = []

                        if self.site_data:
                            self.conn.execute(self.ins_site, self.site_data)
                            self.site_data = []

                        if self.player_data:
                            self.conn.execute(self.ins_player,
                                              self.player_data)
                            self.player_data = []

                        if self.annotator_data:
                            self.conn.execute(self.ins_annotator,
                                              self.annotator_data)
                            self.annotator_data = []

                        if self.source_data:
                            self.conn.execute(self.ins_source, self.source_data)
                            self.source_data = []

                        self.conn.execute(self.ins_game, self.game_data)
                        self.game_data = []

                        if self.bitboard_data:
                            self.conn.execute(self.ins_bitboard, self.bitboard_data)
                            self.bitboard_data = []

                            self.conn.execute(self.ins_stat, self.stat_ins_data)
                            self.conn.execute(self.upd_stat, self.stat_upd_data)
                            self.stat_ins_data = []
                            self.stat_upd_data = []

                        if progressbar is not None:
                            GLib.idle_add(progressbar.set_fraction, i / float(all_games))
                            GLib.idle_add(progressbar.set_text, "%s games from %s imported" % (i, basename))
                        else:
                            print(pgnfile, i)

                if self.event_data:
                    self.conn.execute(self.ins_event, self.event_data)
                    self.event_data = []

                if self.site_data:
                    self.conn.execute(self.ins_site, self.site_data)
                    self.site_data = []

                if self.player_data:
                    self.conn.execute(self.ins_player, self.player_data)
                    self.player_data = []

                if self.annotator_data:
                    self.conn.execute(self.ins_annotator, self.annotator_data)
                    self.annotator_data = []

                if self.source_data:
                    self.conn.execute(self.ins_source, self.source_data)
                    self.source_data = []

                if self.game_data:
                    self.conn.execute(self.ins_game, self.game_data)
                    self.game_data = []

                if self.bitboard_data:
                    self.conn.execute(self.ins_bitboard, self.bitboard_data)
                    self.bitboard_data = []

                    self.conn.execute(self.ins_stat, self.stat_ins_data)
                    self.conn.execute(self.upd_stat, self.stat_upd_data)
                    self.stat_ins_data = []
                    self.stat_upd_data = []

                if progressbar is not None:
                    GLib.idle_add(progressbar.set_fraction, i / float(all_games))
                    GLib.idle_add(progressbar.set_text, "%s games from %s imported" % (i, basename))
                else:
                    print(pgnfile, i)
                trans.commit()

            except SQLAlchemyError as e:
                trans.rollback()
                print("Importing %s failed! \n%s" % (pgnfile, e))

    def print_db(self):
        a1 = event.alias()
        a2 = site.alias()
        a3 = player.alias()
        a4 = player.alias()

        s = select(
            [game.c.id, a1.c.name.label('event'), a2.c.name.label('site'),
             a3.c.name.label('white'), a4.c.name.label('black'),
             game.c.date_year, game.c.date_month, game.c.date_day, game.c.eco,
             game.c.result, game.c.white_elo, game.c.black_elo],
            and_(game.c.event_id == a1.c.id, game.c.site_id == a2.c.id,
                 game.c.white_id == a3.c.id,
                 game.c.black_id == a4.c.id)).where(and_(
                     a3.c.name.startswith(u"Réti"), a4.c.name.startswith(u"Van Nüss")))

        result = self.conn.execute(s)
        games = result.fetchall()
        for g in games:
            print("%s %s %s %s %s %s %s %s %s %s %s %s" %
                  (g['id'], g['event'], g['site'], g['white'], g['black'],
                   g[5], g[6], g[7], g['eco'], reprResult[g['result']],
                   g['white_elo'], g['black_elo']))


class FIDEPlayersImport():
    def __init__(self, engine):
        self.engine = engine
        self.conn = self.engine.connect()
        self.CHUNK = 1000
        self.cancel = False

    def do_cancel(self):
        GLib.idle_add(self.progressbar.set_text, "")
        self.cancel = True

    def import_players(self, progressbar=None):
        self.progressbar = progressbar

        filename = "http://ratings.fide.com/download/players_list.zip"
        filename = download_file(filename, progressbar=progressbar)
        # filename = "/tmp/players_list.zip"
        if filename is None:
            return

        ins_player = insert_or_ignore(self.engine, player.insert())
        player_data = []

        zf = zipfile.ZipFile(filename, "r")
        basename = "players_list_foa.txt"
        size = zf.getinfo(basename).file_size

        with io.TextIOWrapper(zf.open(basename)) as f:
            if progressbar is not None:
                GLib.idle_add(progressbar.set_text, "Pocessing %s ..." % basename)
            else:
                print("Processing %s ..." % basename)

            # use transaction to avoid autocommit slowness
            trans = self.conn.begin()
            i = 0
            try:
                for line in f:
                    if self.cancel:
                        trans.rollback()
                        return

                    if line.startswith("ID"):
                        all_players = size / len(line) - 1
                        continue
                    i += 1

                    title = line[84:88].rstrip()
                    title = title if title else None

                    elo = line[113:117].rstrip()
                    elo = int(elo) if elo else None

                    born = line[152:156].rstrip()
                    born = int(born) if born else None

                    player_data.append({
                        "fideid": int(line[:14]),
                        "name": line[15:75].rstrip(),
                        "fed": line[76:79],
                        "sex": line[80:81],
                        "title": title,
                        "elo": elo,
                        "born": born,
                    })

                    if len(player_data) >= self.CHUNK:
                        self.conn.execute(ins_player, player_data)
                        player_data = []

                        if progressbar is not None:
                            GLib.idle_add(progressbar.set_fraction, i / float(all_players))
                            GLib.idle_add(progressbar.set_text, "%s / %s from %s imported" % (i, all_players, basename))
                        else:
                            print(basename, i)

                if player_data:
                    self.conn.execute(ins_player, player_data)

                trans.commit()

            except:
                trans.rollback()
                raise


def read_games(handle):
    in_tags = False

    tags = []
    moves = []

    for line in handle:
        line = line.lstrip()
        if not line:
            continue
        elif line.startswith("%"):
            continue

        if line.startswith("["):
            if tagre.match(line) is not None:
                if not in_tags:
                    # new game starting
                    if moves:
                        yield ("".join(tags), "".join(moves))
                        tags = []
                        moves = []

                    in_tags = True
                tags.append(line)
            else:
                if not in_tags:
                    moves.append(line)
        else:
            in_tags = False
            moves.append(line)
    if moves:
        yield ("".join(tags), "".join(moves))


if __name__ == "__main__":
    imp = PgnImport(get_engine(None))

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        with Timer() as t:
            if arg[-4:].lower() in (".pgn", ".zip"):
                if os.path.isfile(arg):
                    imp.do_import(arg)
            elif os.path.exists(arg):
                for file in sorted(os.listdir(arg)):
                    if file[-4:].lower() in (".pgn", ".zip"):
                        imp.do_import(os.path.join(arg, file))
        print("Elapsed time (secs): %s" % t.elapsed_secs)
    else:
        path = os.path.abspath(os.path.dirname(__file__))
        with Timer() as t:
            imp.do_import(os.path.join('../../../testing/gamefiles',
                                       "annotated.pgn"))
            imp.do_import(os.path.join('../../../testing/gamefiles',
                                       "world_matches.pgn"))
            imp.do_import(os.path.join('../../../testing/gamefiles',
                                       "dortmund.pgn"))
        print("Elapsed time (secs): %s" % t.elapsed_secs)
        print("Old: 28.68")
    imp.print_db()

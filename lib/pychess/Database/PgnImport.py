# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import io
import os
import sys
import tempfile
import zipfile
from array import array

from gi.repository import GLib, GObject

from sqlalchemy import bindparam, select, func, and_
from sqlalchemy.exc import ProgrammingError

from pychess.compat import unicode, urlopen, HTTPError, URLError
from pychess.Utils.const import FEN_START, reprResult
from pychess.Variants import name2variant
# from pychess.System import profile_me
from pychess.System import Timer
from pychess.System.protoopen import protoopen, PGN_ENCODING
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Savers.pgnbase import pgn_load
from pychess.Database.dbwalk import walk
from pychess.Database.model import DB_MAXINT_SHIFT, \
    event, site, player, game, annotator, bitboard, tag_game, source


GAME, EVENT, SITE, PLAYER, ANNOTATOR, SOURCE = range(6)

removeDic = {
    ord(u"'"): None,
    ord(u","): None,
    ord(u"."): None,
    ord(u"-"): None,
    ord(u" "): None,
}


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

        self.ins_event = event.insert()
        self.ins_site = site.insert()
        self.ins_player = player.insert()
        self.ins_annotator = annotator.insert()
        self.ins_source = source.insert()
        self.ins_game = game.insert()
        self.ins_bitboard = bitboard.insert()
        self.ins_tag_game = tag_game.insert()

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

        self.perfix_stmt = select([player.c.id]).where(player.c.name.startswith(bindparam('name')))

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
        #elif field == PLAYER:
            #result = None
            #trans = self.conn.begin()
            #try:
                #result = self.engine.execute(self.perfix_stmt, name=name).first()
                #trans.commit()
            #except:
                #trans.rollback()
            #if result is not None:
                #return result[0]

        if field == SOURCE:
            name_data.append({'name': orig_name, 'info': info})
        else:
            name_data.append({'name': orig_name})
        name_dict[name] = self.next_id[field]
        self.next_id[field] += 1
        return name_dict[name]

    def ini_names(self, name_table, field):
        if field != GAME:
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
                self.ource_dict = name_dict

        s = select([func.max(name_table.c.id).label('maxid')])
        maxid = self.conn.execute(s).scalar()
        if maxid is None:
            next_id = 1
        else:
            next_id = maxid + 1

        return next_id

    def on_timeout(self, user_data):
        if self.pulse:
            self.progressbar.pulse()
            return True
        else:
            return False

    # @profile_me
    def do_import(self, filename, info=None, progressbar=None):
        self.progressbar = progressbar
        if progressbar is not None:
            self.pulse = True
            self.timeout_id = GObject.timeout_add(50, self.on_timeout, None)

        # collect new names not in they dict yet
        self.event_data = []
        self.site_data = []
        self.player_data = []
        self.annotator_data = []
        self.source_data = []

        # collect new games and commit them in big chunks for speed
        self.game_data = []
        self.bitboard_data = []
        self.tag_game_data = []

        if filename.startswith("http://"):
            filename = download_file(filename, progressbar=progressbar)
            if filename is None:
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
                cf = pgn_load(protoopen(pgnfile))
            else:
                pgn_file = io.TextIOWrapper(zf.open(pgnfile), encoding=PGN_ENCODING, newline='')
                cf = pgn_load(pgn_file)

            if progressbar is not None:
                self.pulse = False

            all_games = len(cf.games)
            self.CHUNK = 1000 if all_games > 5000 else 100

            get_tag = cf._getTag
            get_id = self.get_id
            # use transaction to avoid autocommit slowness
            trans = self.conn.begin()
            try:
                for i in range(all_games):
                    # print i+1#, cf.get_player_names(i)
                    movelist = array("H")
                    comments = []
                    cf.error = None

                    fenstr = get_tag(i, "FEN")
                    variant = cf.get_variant(i)

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
                        board = LBoard(variant)
                    else:
                        variant = 0
                        board = LBoard()

                    if fenstr:
                        try:
                            board.applyFen(fenstr)
                        except SyntaxError as e:
                            print(_(
                                "The game #%s can't be loaded, because of an error parsing FEN")
                                % (i + 1), e.args[0])
                            continue
                    else:
                        board.applyFen(FEN_START)

                    boards = [board]
                    movetext = cf.get_movetext(i)

                    # parse movetext to create boards tree structure
                    boards = cf.parse_string(movetext, boards[0], -1, pgn_import=True)

                    if cf.error is not None:
                        print("ERROR in game #%s" % (i + 1), cf.error.args[0])
                        continue

                    # create movelist and comments from boards tree
                    walk(boards[0], movelist, comments)

                    white = get_tag(i, 'White')
                    black = get_tag(i, 'Black')

                    if not movelist:
                        if (not comments) and (not white) and (not black):
                            print("empty game")
                            continue

                    event_id = get_id(get_tag(i, 'Event'), event, EVENT)

                    site_id = get_id(get_tag(i, 'Site'), site, SITE)

                    game_date = get_tag(i, 'Date')
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

                    game_round = get_tag(i, 'Round')

                    white_fide_id = get_tag(i, 'WhiteFideId')
                    black_fide_id = get_tag(i, 'BlackFideId')

                    white_id = get_id(unicode(white), player, PLAYER, fide_id=white_fide_id)
                    black_id = get_id(unicode(black), player, PLAYER, fide_id=black_fide_id)

                    result = cf.get_result(i)

                    white_elo = get_tag(i, 'WhiteElo')
                    white_elo = int(white_elo) if white_elo and white_elo.isdigit() else None

                    black_elo = get_tag(i, 'BlackElo')
                    black_elo = int(black_elo) if black_elo and black_elo.isdigit() else None

                    ply_count = get_tag(i, "PlyCount")

                    time_control = get_tag(i, "TimeControl")

                    eco = get_tag(i, "ECO")
                    eco = eco[:3] if eco else None

                    fen = get_tag(i, "FEN")

                    board_tag = get_tag(i, "Board")

                    annotator_id = get_id(get_tag(i, "Annotator"), annotator, ANNOTATOR)

                    source_id = get_id(unicode(pgnfile), source, SOURCE, info=info)

                    game_id = self.next_id[GAME]
                    self.next_id[GAME] += 1

                    for ply, board in enumerate(boards):
                        bb = board.friends[0] | board.friends[1]
                        # Avoid to include mate in x .pgn collections and similar in opening tree
                        if fen and "/pppppppp/8/8/8/8/PPPPPPPP/" not in fen:
                            ply = -1
                        self.bitboard_data.append({
                            'game_id': game_id,
                            'ply': ply,
                            'bitboard': bb - DB_MAXINT_SHIFT,
                        })

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

                        if progressbar is not None:
                            GLib.idle_add(progressbar.set_fraction, (i + 1) / float(all_games))
                            GLib.idle_add(progressbar.set_text, "%s / %s from %s imported" % (i + 1, all_games, basename))
                        else:
                            print(pgnfile, i + 1)

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

                if progressbar is not None:
                    GLib.idle_add(progressbar.set_fraction, (i + 1) / float(all_games))
                    GLib.idle_add(progressbar.set_text, "%s / %s from %s imported" % (i + 1, all_games, basename))
                else:
                    print(pgnfile, i + 1)
                trans.commit()

            except ProgrammingError as e:
                trans.rollback()
                print("Importing %s failed! %s" % (file, e))

    def update_players(self, progressbar=None):
        self.progressbar = progressbar
        if progressbar is not None:
            self.pulse = True
            self.timeout_id = GObject.timeout_add(50, self.on_timeout, None)

        filename = "http://ratings.fide.com/download/players_list.zip"
        filename = download_file(filename, progressbar=progressbar)
        if filename is None:
            return

        # TODO: this is Sqlite specific !!!
        # can't use "OR UPDATE" because it delete+insert records
        # and breaks referential integrity
        ins_player = player.insert().prefix_with("OR IGNORE")
        player_data = []

        zf = zipfile.ZipFile(filename, "r")
        with zf.open("players_list_foa.txt") as f:
            basename = os.path.basename(filename)
            if progressbar is not None:
                GLib.idle_add(progressbar.set_text, "Pocessing %s ..." % basename)
            else:
                print("Processing %s ..." % basename)
            # use transaction to avoid autocommit slowness
            trans = self.conn.begin()
            try:
                for line in f:
                    if line.startswith("ID"):
                        continue

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

                if player_data:
                    self.conn.execute(ins_player, player_data)

                trans.commit()

            except:
                trans.rollback()
                raise

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


if __name__ == "__main__":
    imp = PgnImport()

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

# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import collections
import os
import re
import tempfile
import zipfile

from gi.repository import GLib

from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError

from pychess.compat import unicode, urlopen, HTTPError, URLError
from pychess.Utils.const import NORMALCHESS, RUNNING, DRAW, WHITEWON, BLACKWON
from pychess.Variants import name2variant
from pychess.System.protoopen import protoopen, protosave
from pychess.Database.model import event, site, player, game, annotator, tag_game, source


TAG_REGEX = re.compile(r"\[([a-zA-Z0-9_]+)\s+\"(.*)\"\]")

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
    def __init__(self, chessfile, append_pgn=False):
        self.chessfile = chessfile
        self.append_pgn = append_pgn
        self.db_handle = chessfile.handle
        self.engine = chessfile.engine
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

    def get_id(self, name, name_table, field, info=None):
        if not name:
            return None

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

    def do_import(self, filename, info=None, progressbar=None):
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
            with zipfile.ZipFile(filename, "r") as zf:
                path = os.path.dirname(filename)
                files = [os.path.join(path, f) for f in zf.namelist() if f.lower().endswith(".pgn")]
                zf.extractall(path)
        else:
            files = [filename]

        for pgnfile in files:
            base_offset = self.chessfile.size if self.append_pgn else 0

            basename = os.path.basename(pgnfile)
            if progressbar is not None:
                GLib.idle_add(progressbar.set_text, "Reading %s ..." % basename)
            else:
                print("Reading %s ..." % pgnfile)

            size = os.path.getsize(pgnfile)
            handle = protoopen(pgnfile)

            # estimated game count
            all_games = max(size / 840, 1)

            get_id = self.get_id
            # use transaction to avoid autocommit slowness
            trans = self.conn.begin()
            try:
                i = 0
                for offs, tags in read_games(handle):
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
                    else:
                        variant = 0

                    white = tags.get('White')
                    black = tags.get('Black')

                    event_id = get_id(tags.get('Event'), event, EVENT)

                    site_id = get_id(tags.get('Site'), site, SITE)

                    game_date = tags['Date'].strip()
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

                    white_id = get_id(unicode(white), player, PLAYER)
                    black_id = get_id(unicode(black), player, PLAYER)

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

                    self.next_id[GAME] += 1

                    ply_count = tags.get("PlyCount")

                    self.game_data.append({
                        'offset': base_offset + int(offs),
                        'offset8': (int(offs) >> 3) << 3,
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

                        if progressbar is not None:
                            GLib.idle_add(progressbar.set_fraction, i / float(all_games))
                            GLib.idle_add(progressbar.set_text, "%s game headers from %s imported" % (i, basename))
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

                if progressbar is not None:
                    GLib.idle_add(progressbar.set_fraction, i / float(all_games))
                    GLib.idle_add(progressbar.set_text, "%s game headers from %s imported" % (i, basename))
                else:
                    print(pgnfile, i)
                trans.commit()

                if self.append_pgn:
                    # reopen database to write
                    self.db_handle.close()
                    self.db_handle = protosave(self.chessfile.path, self.append_pgn)

                    print("Append from %s to %s" % (pgnfile, self.chessfile.path))
                    handle.seek(0)
                    for line in handle:
                        self.db_handle.write(line)
                    self.db_handle.close()

                self.chessfile.handle = protoopen(self.chessfile.path)

            except SQLAlchemyError as e:
                trans.rollback()
                print("Importing %s failed! \n%s" % (pgnfile, e))


def read_games(handle):
    """Based on chess.pgn.scan_headers() from Niklas Fiekas python-chess"""
    in_comment = False

    game_headers = None
    game_pos = None

    last_pos = 0
    line = handle.readline()

    # scoutfish creates game offsets at previous game end
    line_end_fix = 2 if line.endswith("\r\n") else 1

    while line:
        # Skip single line comments.
        if line.startswith("%"):
            last_pos += len(line)
            line = handle.readline()
            continue

        # Reading a header tag. Parse it and add it to the current headers.
        if not in_comment and line.startswith("["):
            tag_match = TAG_REGEX.match(line)
            if tag_match:
                if game_pos is None:
                    game_headers = collections.defaultdict(str)
                    game_pos = last_pos

                game_headers[tag_match.group(1)] = tag_match.group(2)

                last_pos += len(line)
                line = handle.readline()
                continue

        # Reading movetext. Update parser state in_comment in order to skip
        # comments that look like header tags.
        if (not in_comment and "{" in line) or (in_comment and "}" in line):
            in_comment = line.rfind("{") > line.rfind("}")

        # Reading movetext. If there were headers, previously, those are now
        # complete and can be yielded.
        if game_pos is not None:
            yield max(0, game_pos - line_end_fix), game_headers
            game_pos = None

        last_pos += len(line)
        line = handle.readline()

    # Yield the headers of the last game.
    if game_pos is not None:
        yield max(0, game_pos - line_end_fix), game_headers

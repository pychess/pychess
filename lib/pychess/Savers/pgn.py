# -*- coding: UTF-8 -*-

import shutil
import collections
import os
from io import StringIO
from os.path import getmtime
import platform
import re
import sys
import textwrap

from gi.repository import GLib

import pexpect

from sqlalchemy import String

from pychess.external.scoutfish import Scoutfish
from pychess.external.chess_db import Parser

from pychess.Utils.const import WHITE, BLACK, reprResult, FEN_START, FEN_EMPTY, \
    WON_RESIGN, DRAW, BLACKWON, WHITEWON, NORMALCHESS, DRAW_AGREE, FIRST_PAGE, PREV_PAGE, NEXT_PAGE, \
    ABORTED_REASONS, ADJOURNED_REASONS, WON_CALLFLAG, DRAW_ADJUDICATION, WON_ADJUDICATION, \
    WHITE_ENGINE_DIED, BLACK_ENGINE_DIED, RUNNING, TOOL_NONE, TOOL_CHESSDB, TOOL_SCOUTFISH

from pychess.System import conf
from pychess.System.Log import log
from pychess.System.protoopen import PGN_ENCODING
from pychess.System.prefix import getEngineDataPrefix
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.GameModel import GameModel
from pychess.Utils.lutils.lmove import toSAN, parseSAN, ParsingError
from pychess.Utils.Move import Move
from pychess.Utils.elo import get_elo_rating_change_pgn
from pychess.Utils.logic import getStatus
from pychess.Variants import name2variant, NormalBoard, variants
from pychess.widgets.ChessClock import formatTime
from pychess.Savers.ChessFile import ChessFile, LoadingError
from pychess.Savers.database import col2label, TagDatabase, parseDateTag
from pychess.Database import model as dbmodel
from pychess.Database.PgnImport import TAG_REGEX, pgn2Const, PgnImport
from pychess.Database.model import game, create_indexes, drop_indexes, metadata, ini_schema_version

__label__ = _("Chess Game")
__ending__ = "pgn"
__append__ = True


# token categories
COMMENT_REST, COMMENT_BRACE, COMMENT_NAG, \
    VARIATION_START, VARIATION_END, \
    RESULT, FULL_MOVE, MOVE, MOVE_COMMENT = range(1, 10)

pattern = re.compile(r"""
    (\;.*?[\n\r])        # comment, rest of line style
    |(\{.*?\})           # comment, between {}
    |(\$[0-9]+)          # comment, Numeric Annotation Glyph
    |(\()                # variation start
    |(\))                # variation end
    |(\*|1-0|0-1|1/2)    # result (spec requires 1/2-1/2 for draw, but we want to tolerate simple 1/2 too)
    |(
    ([a-hKkQqRrBNnMmSsF][a-hxKQRBNMSF1-8+#=\-]{1,6}
    |[PNBRQMSFK]@[a-h][1-8][+#]?  # drop move
    |o\-?o(?:\-?o)?      # castling notation using letter 'o' with or without '-'
    |O\-?O(?:\-?O)?      # castling notation using letter 'O' with or without '-'
    |0\-0(?:\-0)?        # castling notation using zero with required '-'
    |\-\-)               # non standard '--' is used for null move inside variations
    ([\?!]{1,2})*
    )    # move (full, count, move with ?!, ?!)
    """, re.VERBOSE | re.DOTALL)

move_eval_re = re.compile("\[%eval\s+([+\-])?(?:#)?(\d+)(?:[,\.](\d{1,2}))?(?:/(\d{1,2}))?\]")
move_time_re = re.compile("\[%emt\s+(\d:)?(\d{1,2}:)?(\d{1,4})(?:\.(\d{1,3}))?\]")

# Chessbase style circles/arrows {[%csl Ra3][%cal Gc2c3,Rc3d4]}
comment_circles_re = re.compile("\[%csl\s+((?:[RGBY]\w{2},?)+)\]")
comment_arrows_re = re.compile("\[%cal\s+((?:[RGBY]\w{4},?)+)\]")

# Mandatory tags (except "Result")
mandatory_tags = ("Event", "Site", "Date", "Round", "White", "Black")


def msToClockTimeTag(ms):
    """
    Converts milliseconds to a chess clock time string in 'WhiteClock'/
    'BlackClock' PGN header format
    """
    msec = ms % 1000
    sec = ((ms - msec) % (1000 * 60)) / 1000
    minute = ((ms - sec * 1000 - msec) % (1000 * 60 * 60)) / (1000 * 60)
    hour = ((ms - minute * 1000 * 60 - sec * 1000 - msec) %
            (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)
    return "%01d:%02d:%02d.%03d" % (hour, minute, sec, msec)


def parseClockTimeTag(tag):
    """
    Parses 'WhiteClock'/'BlackClock' PGN headers and returns the time the
    player playing that color has left on their clock in milliseconds
    """
    match = re.match("(\d{1,2}):(\d\d):(\d\d).(\d{1,3})", tag)
    if match:
        hour, minute, sec, msec = match.groups()
        return int(msec) + int(sec) * 1000 + int(minute) * 60 * 1000 + int(
            hour) * 60 * 60 * 1000


def parseTimeControlTag(tag):
    """
    Parses 'TimeControl' PGN header and returns the time and gain the
    players have on game start in seconds
    """
    match = re.match("^(\d+)\+?(\-?\d+)?$", tag)
    if match:
        secs, gain = match.groups()
        return int(secs), int(gain) if gain is not None else 0, 0
    else:
        match = re.match("^(\d+)\/(\d+)$", tag)
        if match:
            moves, secs = match.groups()
            return int(secs), 0, int(moves)
        else:
            return None


def save(handle, model, position=None, flip=False):
    """ Saves the game from GameModel to .pgn """
    processed_tags = []

    def write_tag(tag, value, roster=False):
        nonlocal processed_tags
        if tag in processed_tags or (not roster and not value):
            return
        try:
            pval = str(value)
            pval = pval.replace("\\", "\\\\")
            pval = pval.replace("\"", "\\\"")
            print('[%s "%s"]' % (tag, pval), file=handle)
        except UnicodeEncodeError:
            pval = bytes(pval, "utf-8").decode(PGN_ENCODING, errors="ignore")
            print('[%s "%s"]' % (tag, pval), file=handle)
        processed_tags = processed_tags + [tag]

    # Mandatory ordered seven-tag roster
    status = reprResult[model.status]
    for tag in mandatory_tags:
        value = model.tags[tag]
        if tag == "Date":
            y, m, d = parseDateTag(value)
            y = "%04d" % y if y is not None else "????"
            m = "%02d" % m if m is not None else "??"
            d = "%02d" % d if d is not None else "??"
            value = "%s.%s.%s" % (y, m, d)
        elif value == "":
            value = "?"
        write_tag(tag, value, roster=True)
    write_tag("Result", reprResult[model.status], roster=True)

    # Variant
    if model.variant.variant != NORMALCHESS:
        write_tag("Variant", model.variant.cecp_name.capitalize())

    # Initial position
    if model.boards[0].asFen() != FEN_START:
        write_tag("SetUp", "1")
        write_tag("FEN", model.boards[0].asFen())

    # Number of moves
    write_tag("PlyCount", model.ply - model.lowply)

    # Final position
    if model.reason == WON_CALLFLAG:
        value = "time forfeit"
    elif model.reason == WON_ADJUDICATION and model.isEngine2EngineGame():
        value = "rules infraction"
    elif model.reason in (DRAW_ADJUDICATION, WON_ADJUDICATION):
        value = "adjudication"
    elif model.reason == WHITE_ENGINE_DIED:
        value = "white engine died"
    elif model.reason == BLACK_ENGINE_DIED:
        value = "black engine died"
    elif model.reason in ABORTED_REASONS:
        value = "abandoned"
    elif model.reason in ADJOURNED_REASONS:
        value = "unterminated"
    else:
        value = "unterminated" if status == "*" else None
    if value is not None:
        write_tag("Termination", value)

    # ELO and its variation
    if conf.get("saveRatingChange"):
        welo = model.tags["WhiteElo"]
        belo = model.tags["BlackElo"]
        if welo != "" and belo != "":
            write_tag("WhiteRatingDiff", get_elo_rating_change_pgn(model, WHITE))  # Unofficial
            write_tag("BlackRatingDiff", get_elo_rating_change_pgn(model, BLACK))  # Unofficial

    # Time
    if model.timed:
        write_tag('WhiteClock', msToClockTimeTag(int(model.timemodel.getPlayerTime(WHITE) * 1000)))
        write_tag('BlackClock', msToClockTimeTag(int(model.timemodel.getPlayerTime(BLACK) * 1000)))

    # Write all the unprocessed tags
    for tag in model.tags:
        # Debug: print(">> %s = %s" % (tag, str(model.tags[tag])))
        write_tag(tag, model.tags[tag])

    # Discovery of the moves and comments
    save_emt = conf.get("saveEmt")
    save_eval = conf.get("saveEval")
    result = []
    walk(model.boards[0].board, result, model, save_emt, save_eval)

    # Alignment of the fetched elements
    indented = conf.get("indentPgn")
    if indented:
        buffer = ""
        depth = 0
        crlf = False
        for text in result:
            # De/Indentation
            crlf = (buffer[-1:] if len(buffer) > 0 else "") in ["\r", "\n"]
            if text == "(":
                depth += 1
                if indented and not crlf:
                    buffer += os.linesep
                    crlf = True
            # Space between each term
            last = buffer[-1:] if len(buffer) > 0 else ""
            crlf = last in ["\r", "\n"]
            if not crlf and last != " " and last != "\t" and last != "(" and not text.startswith("\r") and not text.startswith("\n") and text != ")" and len(buffer) > 0:
                buffer += " "
            # New line for a new main move
            if len(buffer) == 0 or (indented and depth == 0 and last != "\r" and last != "\n" and re.match("^[0-9]+\.", text) is not None):
                buffer += os.linesep
                crlf = True
            # Alignment
            if crlf and depth > 0:
                for j in range(0, depth):
                    buffer += "    "
            # Term
            buffer += text
            if indented and text == ")":
                buffer += os.linesep
                crlf = True
                depth -= 1
    else:
        # Add new line to separate tag section and movetext
        print('', file=handle)
        buffer = textwrap.fill(" ".join(result), width=80)

    # Final
    status = reprResult[model.status]
    print(buffer, status, file=handle)
    # Add new line to separate next game
    print('', file=handle)

    output = handle.getvalue() if isinstance(handle, StringIO) else ""
    handle.close()
    return output


def walk(node, result, model, save_emt=False, save_eval=False, vari=False):
    """Prepares a game data for .pgn storage.
       Recursively walks the node tree to collect moves and comments
       into a resulting movetext string.

       Arguments:
       node - list (a tree of lboards created by the pgn parser)
       result - str (movetext strings)"""

    while True:
        if node is None:
            break

        # Initial game or variation comment
        if node.prev is None:
            for child in node.children:
                if isinstance(child, str):
                    result.append("{%s}%s" % (child, os.linesep))
            node = node.next
            continue

        movecount = move_count(node,
                               black_periods=(save_emt or save_eval) and
                               "TimeControl" in model.tags)
        if movecount is not None:
            if movecount:
                result.append(movecount)
            move = node.lastMove
            result.append(toSAN(node.prev, move))
            if (save_emt or save_eval) and not vari:
                emt_eval = ""
                if "TimeControl" in model.tags and save_emt:
                    elapsed = model.timemodel.getElapsedMoveTime(
                        node.plyCount - model.lowply)
                    emt_eval = "[%%emt %s]" % formatTime(elapsed, clk2pgn=True)
                if node.plyCount in model.scores and save_eval:
                    moves, score, depth = model.scores[node.plyCount]
                    if node.color == BLACK:
                        score = -score
                    emt_eval += "[%%eval %0.2f/%s]" % (score / 100.0, depth)
                if emt_eval:
                    result.append("{%s}" % emt_eval)

        for nag in node.nags:
            if nag:
                result.append(nag)

        for child in node.children:
            if isinstance(child, str):
                # comment
                if child:
                    result.append("{%s}" % child)
            else:
                # variations
                if node.fen_was_applied:
                    result.append("(")
                    walk(child[0],
                         result,
                         model,
                         save_emt,
                         save_eval,
                         vari=True)
                    result.append(")")
                    # variation after last played move is not valid pgn
                    # but we will save it as in comment
                else:
                    result.append("{%s:" % _("Analyzer's primary variation"))
                    walk(child[0],
                         result,
                         model,
                         save_emt,
                         save_eval,
                         vari=True)
                    result.append("}")

        if node.next:
            node = node.next
        else:
            break


def move_count(node, black_periods=False):
    mvcount = None
    if node.fen_was_applied:
        ply = node.plyCount
        if ply % 2 == 1:
            mvcount = "%d." % (ply // 2 + 1)
        # initial game move, or initial variation move
        # it can be the same position as the main line! this is the reason using id()
        elif node.prev.prev is None or id(node) != id(
                node.prev.next) or black_periods:
            mvcount = "%d..." % (ply // 2)
        elif node.prev.children:
            # move after real(not [%foo bar]) comment
            need_mvcount = False
            for child in node.prev.children:
                if isinstance(child, str):
                    if not child.startswith("[%"):
                        need_mvcount = True
                        break
                else:
                    need_mvcount = True
                    break
            if need_mvcount:
                mvcount = "%d..." % (ply // 2)
            else:
                mvcount = ""
        else:
            mvcount = ""
    return mvcount


def load(handle, progressbar=None):
    return PGNFile(handle, progressbar)


try:
    with open("/proc/cpuinfo") as f:
        cpuinfo = f.read()
except OSError:
    cpuinfo = ""

BITNESS = "64" if platform.machine().endswith('64') else "32"
MODERN = "-modern" if "popcnt" in cpuinfo else ""
EXT = ".exe" if sys.platform == "win32" else ""

altpath = getEngineDataPrefix()

scoutfish = "scoutfish_x%s%s%s" % (BITNESS, MODERN, EXT)
scoutfish_path = shutil.which(scoutfish, mode=os.X_OK, path=altpath)

parser = "parser_x%s%s%s" % (BITNESS, MODERN, EXT)
chess_db_path = shutil.which(parser, mode=os.X_OK, path=altpath)


class PGNFile(ChessFile):
    def __init__(self, handle, progressbar=None):
        ChessFile.__init__(self, handle)
        self.handle = handle
        self.progressbar = progressbar
        self.pgn_is_string = isinstance(handle, StringIO)

        if self.pgn_is_string:
            self.games = [self.load_game_tags(), ]
        else:
            self.skip = 0
            self.limit = 100
            self.order_col = game.c.offset
            self.is_desc = False
            self.reset_last_seen()

            # filter expressions to .sqlite .bin .scout
            self.tag_query = None
            self.fen = None
            self.scout_query = None

            self.scoutfish = None
            self.chess_db = None

            self.sqlite_path = os.path.splitext(self.path)[0] + '.sqlite'
            self.engine = dbmodel.get_engine(self.sqlite_path)
            self.tag_database = TagDatabase(self.engine)

            self.games, self.offs_ply = self.get_records(0)
            log.info("%s contains %s game(s)" % (self.path, self.count), extra={"task": "SQL"})

    def get_count(self):
        """ Number of games in .pgn database """
        if self.pgn_is_string:
            return len(self.games)
        else:
            return self.tag_database.count
    count = property(get_count)

    def get_size(self):
        """ Size of .pgn file in bytes """
        return os.path.getsize(self.path)
    size = property(get_size)

    def close(self):
        self.tag_database.close()
        ChessFile.close(self)

    def init_tag_database(self, importer=None):
        """ Create/open .sqlite database of game header tags """
        # Import .pgn header tags to .sqlite database

        sqlite_path = self.path.replace(".pgn", ".sqlite")
        if os.path.isfile(self.path) and os.path.isfile(sqlite_path) and getmtime(self.path) > getmtime(sqlite_path):
            metadata.drop_all(self.engine)
            metadata.create_all(self.engine)
            ini_schema_version(self.engine)

        size = self.size
        if size > 0 and self.tag_database.count == 0:
            if size > 10000000:
                drop_indexes(self.engine)
            if self.progressbar is not None:
                GLib.idle_add(self.progressbar.set_text, _("Importing game headers..."))
            if importer is None:
                importer = PgnImport(self)
            importer.initialize()
            importer.do_import(self.path, progressbar=self.progressbar)
            if size > 10000000 and not importer.cancel:
                create_indexes(self.engine)

        return importer

    def init_chess_db(self):
        """ Create/open polyglot .bin file with extra win/loss/draw stats
            using chess_db parser from https://github.com/mcostalba/chess_db
        """
        if chess_db_path is not None and self.path and self.size > 0:
            try:
                if self.progressbar is not None:
                    GLib.idle_add(self.progressbar.set_text, _("Creating .bin index file..."))
                self.chess_db = Parser(engine=(chess_db_path, ))
                self.chess_db.open(self.path)
                bin_path = os.path.splitext(self.path)[0] + '.bin'
                if not os.path.isfile(bin_path):
                    log.debug("No valid games found in %s" % self.path)
                    self.chess_db = None
                elif getmtime(self.path) > getmtime(bin_path):
                    self.chess_db.make()
            except OSError as err:
                self.chess_db = None
                log.warning("Failed to sart chess_db parser. OSError %s %s" % (err.errno, err.strerror))
            except pexpect.TIMEOUT:
                self.chess_db = None
                log.warning("chess_db parser failed (pexpect.TIMEOUT)")
            except pexpect.EOF:
                self.chess_db = None
                log.warning("chess_db parser failed (pexpect.EOF)")

    def init_scoutfish(self):
        """ Create/open .scout database index file to help querying
            using scoutfish from https://github.com/mcostalba/scoutfish
        """
        if scoutfish_path is not None and self.path and self.size > 0:
            try:
                if self.progressbar is not None:
                    GLib.idle_add(self.progressbar.set_text, _("Creating .scout index file..."))
                self.scoutfish = Scoutfish(engine=(scoutfish_path, ))
                self.scoutfish.open(self.path)
                scout_path = os.path.splitext(self.path)[0] + '.scout'
                if getmtime(self.path) > getmtime(scout_path):
                    self.scoutfish.make()
            except OSError as err:
                self.scoutfish = None
                log.warning("Failed to sart scoutfish. OSError %s %s" % (err.errno, err.strerror))
            except pexpect.TIMEOUT:
                self.scoutfish = None
                log.warning("scoutfish failed (pexpect.TIMEOUT)")
            except pexpect.EOF:
                self.scoutfish = None
                log.warning("scoutfish failed (pexpect.EOF)")

    def get_book_moves(self, fen):
        """ Get move-games-win-loss-draw stat of fen position """
        rows = []
        if self.chess_db is not None:
            move_stat = self.chess_db.find("limit %s skip %s %s" % (1, 0, fen))
            for mstat in move_stat["moves"]:
                rows.append((mstat["move"], int(mstat["games"]), int(mstat["wins"]), int(mstat["losses"]), int(mstat["draws"])))
        return rows

    def has_position(self, fen):
        # ChessDB (prioritary)
        if self.chess_db is not None:
            ret = self.chess_db.find("limit %s skip %s %s" % (1, 0, fen))
            if len(ret["moves"]) > 0:
                return TOOL_CHESSDB, True
        # Scoutfish (alternate by approximation)
        if self.scoutfish is not None:
            q = {"limit": 1, "skip": 0, "sub-fen": fen}
            ret = self.scoutfish.scout(q)
            if ret["match count"] > 0:
                return TOOL_SCOUTFISH, True
        return TOOL_NONE, False

    def set_tag_order(self, order_col, is_desc):
        self.order_col = order_col
        self.is_desc = is_desc
        self.tag_database.build_order_by(self.order_col, self.is_desc)

    def reset_last_seen(self):
        col_max = "ZZZ" if isinstance(self.order_col.type, String) else 2 ** 32
        col_min = "" if isinstance(self.order_col.type, String) else -1
        if self.is_desc:
            self.last_seen = [(col_max, 2 ** 32)]
        else:
            self.last_seen = [(col_min, -1)]

    def set_tag_filter(self, query):
        """ Set (now prefixing) text and
            create where clause we will use to query header tag .sqlite database
        """
        self.tag_query = query
        self.tag_database.build_where_tags(self.tag_query)

    def set_fen_filter(self, fen):
        """ Set fen string we will use to get game offsets from .bin database """
        if self.chess_db is not None and fen is not None and fen != FEN_START:
            self.fen = fen
        else:
            self.fen = None
            self.tag_database.build_where_offs8(None)

    def set_scout_filter(self, query):
        """ Set json string we will use to get game offsets from  .scout database """
        if self.scoutfish is not None and query:
            self.scout_query = query
        else:
            self.scout_query = None
            self.tag_database.build_where_offs(None)
            self.offs_ply = {}

    def get_offs(self, skip, filtered_offs_list=None):
        """ Get offsets from .scout database and
            create where clause we will use to query header tag .sqlite database
        """
        if self.scout_query:
            limit = (10000 if self.tag_query else self.limit) + 1
            self.scout_query["skip"] = skip
            self.scout_query["limit"] = limit
            move_stat = self.scoutfish.scout(self.scout_query)

            offsets = []
            for mstat in move_stat["matches"]:
                offs = mstat["ofs"]
                if filtered_offs_list is None:
                    offsets.append(offs)
                    self.offs_ply[offs] = mstat["ply"][0]
                elif offs in filtered_offs_list:
                    offsets.append(offs)
                    self.offs_ply[offs] = mstat["ply"][0]

            if filtered_offs_list is not None:
                # Continue scouting until we get enough good offset if needed
                # print(0, move_stat["match count"], len(offsets))
                i = 1
                while len(offsets) < self.limit and move_stat["match count"] == limit:
                    self.scout_query["skip"] = i * limit - 1
                    move_stat = self.scoutfish.scout(self.scout_query)

                    for mstat in move_stat["matches"]:
                        offs = mstat["ofs"]
                        if offs in filtered_offs_list:
                            offsets.append(offs)
                            self.offs_ply[offs] = mstat["ply"][0]

                    # print(i, move_stat["match count"], len(offsets))
                    i += 1

            if len(offsets) > self.limit:
                self.tag_database.build_where_offs(offsets[:self.limit])
            else:
                self.tag_database.build_where_offs(offsets)

    def get_offs8(self, skip, filtered_offs_list=None):
        """ Get offsets from .bin database and
            create where clause we will use to query header tag .sqlite database
        """
        if self.fen:
            move_stat = self.chess_db.find("limit %s skip %s %s" % (self.limit, skip, self.fen))

            offsets = []
            for mstat in move_stat["moves"]:
                offs = mstat["pgn offsets"]
                if filtered_offs_list is None:
                    offsets += offs
                elif offs in filtered_offs_list:
                    offsets += offs

            if len(offsets) > self.limit:
                self.tag_database.build_where_offs8(sorted(offsets)[:self.limit])
            else:
                self.tag_database.build_where_offs8(sorted(offsets))

    def get_records(self, direction=FIRST_PAGE):
        """ Get game header tag records from .sqlite database in paginated way """
        if direction == FIRST_PAGE:
            self.skip = 0
            self.reset_last_seen()
        elif direction == NEXT_PAGE:
            if not self.tag_query:
                self.skip += self.limit
        elif direction == PREV_PAGE:
            if len(self.last_seen) == 2:
                self.reset_last_seen()
            elif len(self.last_seen) > 2:
                self.last_seen = self.last_seen[:-2]

            if not self.tag_query and self.skip >= self.limit:
                self.skip -= self.limit

        if self.fen:
            self.reset_last_seen()

        filtered_offs_list = None
        if self.tag_query and (self.fen or self.scout_query):
            filtered_offs_list = self.tag_database.get_offsets_for_tags(self.last_seen[-1])

        if self.fen:
            self.get_offs8(self.skip, filtered_offs_list=filtered_offs_list)

        if self.scout_query:
            self.get_offs(self.skip, filtered_offs_list=filtered_offs_list)
            # No game satisfied scout_query
            if self.tag_database.where_offs is None:
                return [], {}

        records = self.tag_database.get_records(self.last_seen[-1], self.limit)

        if records:
            self.last_seen.append((records[-1][col2label[self.order_col]], records[-1]["Offset"]))
            return records, self.offs_ply
        else:
            return [], {}

    def load_game_tags(self):
        """ Reads header tags from pgn if pgn is a one game only StringIO object """

        header = collections.defaultdict(str)
        header["Id"] = 0
        header["Offset"] = 0
        for line in self.handle.readlines():
            line = line.strip()
            if line.startswith('[') and line.endswith(']'):
                tag_match = TAG_REGEX.match(line)
                if tag_match:
                    value = tag_match.group(2)
                    value = value.replace("\\\"", "\"")
                    value = value.replace("\\\\", "\\")
                    header[tag_match.group(1)] = value
            else:
                break
        return header

    def loadToModel(self, rec, position=-1, model=None):
        """ Parse game text and load game record header tags to a GameModel object """

        if model is None:
            model = GameModel()

        if self.pgn_is_string:
            rec = self.games[0]

        # Load mandatory tags
        for tag in mandatory_tags:
            model.tags[tag] = rec[tag]

        # Load other tags
        for tag in ('WhiteElo', 'BlackElo', 'ECO', 'TimeControl', 'Annotator'):
            model.tags[tag] = rec[tag]

        if self.pgn_is_string:
            for tag in rec:
                if isinstance(rec[tag], str) and rec[tag]:
                    model.tags[tag] = rec[tag]
        else:
            model.info = self.tag_database.get_info(rec)
            extra_tags = self.tag_database.get_exta_tags(rec)
            for et in extra_tags:
                model.tags[et['tag_name']] = et['tag_value']

        if self.pgn_is_string:
            variant = rec["Variant"].capitalize()
        else:
            variant = self.get_variant(rec)

        if model.tags['TimeControl']:
            tc = parseTimeControlTag(model.tags['TimeControl'])
            if tc is not None:
                secs, gain, moves = tc
                model.timed = True
                model.timemodel.secs = secs
                model.timemodel.gain = gain
                model.timemodel.minutes = secs / 60
                model.timemodel.moves = moves
                for tag, color in (('WhiteClock', WHITE), ('BlackClock', BLACK)):
                    if tag in model.tags:
                        try:
                            millisec = parseClockTimeTag(model.tags[tag])
                            # We need to fix when FICS reports negative clock time like this
                            # [TimeControl "180+0"]
                            # [WhiteClock "0:00:15.867"]
                            # [BlackClock "23:59:58.820"]
                            start_sec = (
                                millisec - 24 * 60 * 60 * 1000
                            ) / 1000. if millisec > 23 * 60 * 60 * 1000 else millisec / 1000.
                            model.timemodel.intervals[color][0] = start_sec
                        except ValueError:
                            raise LoadingError(
                                "Error parsing '%s'" % tag)
        fenstr = rec["FEN"]

        if variant:
            if variant not in name2variant:
                raise LoadingError("Unknown variant %s" % variant)

            model.tags["Variant"] = variant
            # Fixes for some non statndard Chess960 .pgn
            if (fenstr is not None) and variant == "Fischerandom":
                parts = fenstr.split()
                parts[0] = parts[0].replace(".", "/").replace("0", "")
                if len(parts) == 1:
                    parts.append("w")
                    parts.append("-")
                    parts.append("-")
                fenstr = " ".join(parts)

            model.variant = name2variant[variant]
            board = LBoard(model.variant.variant)
        else:
            model.variant = NormalBoard
            board = LBoard()

        if fenstr:
            try:
                board.applyFen(fenstr)
                model.tags["FEN"] = fenstr
            except SyntaxError as err:
                board.applyFen(FEN_EMPTY)
                raise LoadingError(
                    _("The game can't be loaded, because of an error parsing FEN"),
                    err.args[0])
        else:
            board.applyFen(FEN_START)

        boards = [board]

        del model.moves[:]
        del model.variations[:]

        self.error = None
        movetext = self.get_movetext(rec)
        boards = self.parse_movetext(movetext, boards[0], position)

        # The parser built a tree of lboard objects, now we have to
        # create the high level Board and Move lists...

        for board in boards:
            if board.lastMove is not None:
                model.moves.append(Move(board.lastMove))

        self.has_emt = False
        self.has_eval = False

        def walk(model, node, path):
            if node.prev is None:
                # initial game board
                board = model.variant(setup=node.asFen(), lboard=node)
            else:
                move = Move(node.lastMove)
                try:
                    board = node.prev.pieceBoard.move(move, lboard=node)
                except Exception:
                    raise LoadingError(
                        _("Invalid move."),
                        "%s%s" % (move_count(node, black_periods=True), move))

            if node.next is None:
                model.variations.append(path + [board])
            else:
                walk(model, node.next, path + [board])

            for child in node.children:
                if isinstance(child, list):
                    if len(child) > 1:
                        # non empty variation, go walk
                        walk(model, child[1], list(path))
                else:
                    if not self.has_emt:
                        self.has_emt = child.find("%emt") >= 0
                    if not self.has_eval:
                        self.has_eval = child.find("%eval") >= 0

        # Collect all variation paths into a list of board lists
        # where the first one will be the boards of mainline game.
        # model.boards will allways point to the current shown variation
        # which will be model.variations[0] when we are in the mainline.
        walk(model, boards[0], [])
        model.boards = model.variations[0]
        self.has_emt = self.has_emt and model.timed
        if self.has_emt or self.has_eval:
            if self.has_emt:
                blacks = len(model.moves) // 2
                whites = len(model.moves) - blacks

                model.timemodel.intervals = [
                    [model.timemodel.intervals[0][0]] * (whites + 1),
                    [model.timemodel.intervals[1][0]] * (blacks + 1),
                ]
                model.timemodel.intervals[0][0] = secs
                model.timemodel.intervals[1][0] = secs
            for ply, board in enumerate(boards):
                for child in board.children:
                    if isinstance(child, str):
                        if self.has_emt:
                            match = move_time_re.search(child)
                            if match:
                                movecount, color = divmod(ply + 1, 2)
                                hour, minute, sec, msec = match.groups()
                                prev = model.timemodel.intervals[color][
                                    movecount - 1]
                                hour = 0 if hour is None else int(hour[:-1])
                                minute = 0 if minute is None else int(minute[:-1])
                                msec = 0 if msec is None else int(msec)
                                msec += int(sec) * 1000 + int(minute) * 60 * 1000 + int(hour) * 60 * 60 * 1000
                                model.timemodel.intervals[color][movecount] = prev - msec / 1000. + gain

                        if self.has_eval:
                            match = move_eval_re.search(child)
                            if match:
                                sign, num, fraction, depth = match.groups()
                                sign = 1 if sign is None or sign == "+" else -1
                                num = int(num)
                                fraction = 0 if fraction is None else int(
                                    fraction)
                                value = sign * (num * 100 + fraction)
                                depth = "" if depth is None else depth
                                if board.color == BLACK:
                                    value = -value
                                model.scores[ply] = ("", value, depth)
            log.debug("pgn.loadToModel: intervals %s" %
                      model.timemodel.intervals)

        # Find the physical status of the game
        model.status, model.reason = getStatus(model.boards[-1])

        # Apply result from .pgn if the last position was loaded
        if position == -1 or len(model.moves) == position - model.lowply:
            if self.pgn_is_string:
                result = rec["Result"]
                if result in pgn2Const:
                    status = pgn2Const[result]
                else:
                    status = RUNNING
            else:
                status = rec["Result"]

            if status in (WHITEWON, BLACKWON) and status != model.status:
                model.status = status
                model.reason = WON_RESIGN
            elif status == DRAW and status != model.status:
                model.status = DRAW
                model.reason = DRAW_AGREE

        if model.timed:
            model.timemodel.movingColor = model.boards[-1].color

        # If parsing gave an error we throw it now, to enlarge our possibility
        # of being able to continue the game from where it failed.
        if self.error:
            raise self.error

        return model

    def parse_movetext(self, string, board, position, variation=False):
        """Recursive parses a movelist part of one game.

           Arguments:
           srting - str (movelist)
           board - lboard (initial position)
           position - int (maximum ply to parse)
           variation- boolean (True if the string is a variation)"""

        boards = []
        boards_append = boards.append

        last_board = board
        if variation:
            # this board used only to hold initial variation comments
            boards_append(LBoard(board.variant))
        else:
            # initial game board
            boards_append(board)

        # status = None
        parenthesis = 0
        v_string = ""
        v_last_board = None
        for m in re.finditer(pattern, string):
            group, text = m.lastindex, m.group(m.lastindex)
            if parenthesis > 0:
                v_string += ' ' + text

            if group == VARIATION_END:
                parenthesis -= 1
                if parenthesis == 0:
                    if last_board.prev is None:
                        errstr1 = _("Error parsing %(mstr)s") % {"mstr": string}
                        self.error = LoadingError(errstr1, "")
                        return boards  # , status

                    v_last_board.children.append(
                        self.parse_movetext(v_string[:-1], last_board.prev, position, variation=True))
                    v_string = ""
                    continue

            elif group == VARIATION_START:
                parenthesis += 1
                if parenthesis == 1:
                    v_last_board = last_board

            if parenthesis == 0:
                if group == FULL_MOVE:
                    if not variation:
                        if position != -1 and last_board.plyCount >= position:
                            break

                    mstr = m.group(MOVE)
                    try:
                        lmove = parseSAN(last_board, mstr)
                    except ParsingError as err:
                        # TODO: save the rest as comment
                        # last_board.children.append(string[m.start():])
                        notation, reason, boardfen = err.args
                        ply = last_board.plyCount
                        if ply % 2 == 0:
                            moveno = "%d." % (ply // 2 + 1)
                        else:
                            moveno = "%d..." % (ply // 2 + 1)
                        errstr1 = _(
                            "The game can't be read to end, because of an error parsing move %(moveno)s '%(notation)s'.") % {
                                'moveno': moveno,
                                'notation': notation}
                        errstr2 = _("The move failed because %s.") % reason
                        self.error = LoadingError(errstr1, errstr2)
                        break
                    except Exception:
                        ply = last_board.plyCount
                        if ply % 2 == 0:
                            moveno = "%d." % (ply // 2 + 1)
                        else:
                            moveno = "%d..." % (ply // 2 + 1)
                        errstr1 = _(
                            "Error parsing move %(moveno)s %(mstr)s") % {
                                "moveno": moveno,
                                "mstr": mstr}
                        self.error = LoadingError(errstr1, "")
                        break

                    new_board = last_board.clone()
                    new_board.applyMove(lmove)

                    if m.group(MOVE_COMMENT):
                        new_board.nags.append(symbol2nag(m.group(
                            MOVE_COMMENT)))

                    new_board.prev = last_board

                    # set last_board next, except starting a new variation
                    if variation and last_board == board:
                        boards[0].next = new_board
                    else:
                        last_board.next = new_board

                    boards_append(new_board)
                    last_board = new_board

                elif group == COMMENT_REST:
                    last_board.children.append(text[1:])

                elif group == COMMENT_BRACE:
                    comm = text.replace('{\r\n', '{').replace('\r\n}', '}')
                    # Preserve new lines of lichess study comments
                    if self.path is not None and "lichess_study_" in self.path:
                        comment = comm[1:-1]
                    else:
                        comm = comm[1:-1].splitlines()
                        comment = ' '.join([line.strip() for line in comm])
                    if variation and last_board == board:
                        # initial variation comment
                        boards[0].children.append(comment)
                    else:
                        last_board.children.append(comment)

                elif group == COMMENT_NAG:
                    last_board.nags.append(text)

                # TODO
                elif group == RESULT:
                    # if text == "1/2":
                    #    status = reprResult.index("1/2-1/2")
                    # else:
                    #    status = reprResult.index(text)
                    break

                else:
                    print("Unknown:", text)

        return boards  # , status

    def get_movetext(self, rec):
        self.handle.seek(rec["Offset"])
        in_comment = False
        lines = []
        line = self.handle.readline()
        if not line.strip():
            line = self.handle.readline()

        while line:
            # escape non-PGN data line
            if line.startswith("%"):
                line = self.handle.readline()
                continue

            # header tag line
            if not in_comment and line.startswith("["):
                line = self.handle.readline()
                continue

            # update in_comment state
            if (not in_comment and "{" in line) or (in_comment and "}" in line):
                in_comment = line.rfind("{") > line.rfind("}")

            # if there is something add it
            if line.strip():
                if not self.pgn_is_string and self.handle.pgn_encoding != PGN_ENCODING:
                    line = line.encode(PGN_ENCODING).decode(self.handle.pgn_encoding)
                lines.append(line)
                line = self.handle.readline()
            # if line is empty it should be the game separator line except...
            elif len(lines) == 0 or in_comment:
                if in_comment:
                    lines.append(line)
                line = self.handle.readline()
            else:
                break
        return "".join(lines)

    def get_variant(self, rec):
        variant = rec["Variant"]
        return variants[variant].cecp_name.capitalize() if variant else ""


nag2symbolDict = {
    "$0": "",
    "$1": "!",
    "$2": "?",
    "$3": "!!",
    "$4": "??",
    "$5": "!?",
    "$6": "?!",
    "$7": "□",  # forced move
    "$8": "□",
    "$9": "??",
    "$10": "=",
    "$11": "=",
    "$12": "=",
    "$13": "∞",  # unclear
    "$14": "+=",
    "$15": "=+",
    "$16": "±",
    "$17": "∓",
    "$18": "+-",
    "$19": "-+",
    "$20": "+--",
    "$21": "--+",
    "$22": "⨀",  # zugzwang
    "$23": "⨀",
    "$24": "◯",  # space
    "$25": "◯",
    "$26": "◯",
    "$27": "◯",
    "$28": "◯",
    "$29": "◯",
    "$32": "⟳",  # development
    "$33": "⟳",
    "$36": "↑",  # initiative
    "$37": "↑",
    "$40": "→",  # attack
    "$41": "→",
    "$44": "~=",  # compensation
    "$45": "=~",
    "$132": "⇆",  # counterplay
    "$133": "⇆",
    "$136": "⨁",  # time
    "$137": "⨁",
    "$138": "⨁",
    "$139": "⨁",
    "$140": "∆",  # with the idea
    "$141": "∇",  # aimed against
    "$142": "⌓",  # better is
    "$146": "N",  # novelty
}

symbol2nagDict = {}
for k, v in nag2symbolDict.items():
    if v not in symbol2nagDict:
        symbol2nagDict[v] = k


def nag2symbol(nag):
    return nag2symbolDict.get(nag, nag)


def symbol2nag(symbol):
    return symbol2nagDict[symbol]

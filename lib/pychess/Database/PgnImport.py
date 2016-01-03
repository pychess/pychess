# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import zipfile
from datetime import date
from array import array

#from .profilehooks import profile

from sqlalchemy import select, Index, func, and_
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.schema import DropIndex

from pychess.compat import unicode
from pychess.Utils.const import *
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Savers.ChessFile import LoadingError
from pychess.Savers.pgnbase import pgn_load
from pychess.Database.dbwalk import walk
from pychess.Database.model import engine, metadata, collection, event,\
                            site, player, game, annotator, ini_collection

CHUNK = 1000

EVENT, SITE, PLAYER, ANNOTATOR, COLLECTION = range(5)

removeDic = {
    ord(unicode("'")): None,
    ord(unicode(",")): None,
    ord(unicode(".")): None,
    ord(unicode("-")): None,
    ord(unicode(" ")): None,
}

LBoard_FEN_START = LBoard()
LBoard_FEN_START.applyFen(FEN_START)

class PgnImport():
    def __init__(self):
        self.conn = engine.connect()
        
        self.ins_collection = collection.insert()
        self.ins_event = event.insert()
        self.ins_site = site.insert()
        self.ins_player = player.insert()
        self.ins_annotator = annotator.insert()
        self.ins_game = game.insert()
        
        self.collection_dict = {}
        self.event_dict = {}
        self.site_dict = {}
        self.player_dict = {}
        self.annotator_dict = {}

        self.next_id = [0, 0, 0, 0, 0]

        self.next_id[COLLECTION] = self.ini_names(collection, COLLECTION)
        self.next_id[EVENT] = self.ini_names(event, EVENT)
        self.next_id[SITE] = self.ini_names(site, SITE)
        self.next_id[PLAYER] = self.ini_names(player, PLAYER)
        self.next_id[ANNOTATOR] = self.ini_names(annotator, ANNOTATOR)

    def get_id(self, name, name_table, field):
        if not name:
            return None
        
        orig_name = name
        if field == COLLECTION:
            name_dict = self.collection_dict
            name_data = self.collection_data
            name = os.path.basename(name)[:-4]
        elif field == EVENT:
            name_dict = self.event_dict
            name_data = self.event_data
        elif field == SITE:
            name_dict = self.site_dict
            name_data = self.site_data
        elif field == ANNOTATOR:
            name_dict = self.annotator_dict
            name_data = self.annotator_data
        elif field == PLAYER:
            name_dict = self.player_dict
            name_data = self.player_data

            # Some .pgn use country after player names
            if name[-4:-3]==" " and name[-3:].isupper():
                name = name[:-4]
            name = name.title().translate(removeDic)

        if name in name_dict:
            return name_dict[name]
        else:
            if field == COLLECTION:
                name_data.append({'source': orig_name, 'name': name})
            else:
                name_data.append({'name': orig_name})
            name_dict[name] = self.next_id[field]
            self.next_id[field] += 1
            return name_dict[name]

    def ini_names(self, name_table, field):
        s = select([name_table])
        name_dict = dict([(n.name.title().translate(removeDic), n.id) for n in self.conn.execute(s)])

        if field == COLLECTION:
            self.collection_dict = name_dict
        elif field == EVENT:
            self.event_dict = name_dict
        elif field == SITE:
            self.site_dict = name_dict
        elif field == PLAYER:
            self.player_dict = name_dict
        elif field == ANNOTATOR:
            self.annotator_dict = name_dict
            
        s = select([func.max(name_table.c.id).label('maxid')])
        maxid = self.conn.execute(s).scalar()
        if maxid is None:
            next_id = 1
        else:
            next_id = maxid + 1

        return next_id

    #@profile
    def do_import(self, filename):
        print(filename)
        # collect new names not in they dict yet
        self.collection_data = []
        self.event_data = []
        self.site_data = []
        self.player_data = []
        self.annotator_data = []
        
        # collect new games and commit them in big chunks for speed
        self.game_data = []

        if filename.lower().endswith(".zip") and zipfile.is_zipfile(filename):
            zf = zipfile.ZipFile(filename, "r")
            files = [f for f in zf.namelist() if f.lower().endswith(".pgn")]
        else:
            zf = None
            files = [filename]
        
        for pgnfile in files:
            if zf is None:
                cf = pgn_load(open(pgnfile, "rU"))
            else:
                cf = pgn_load(zf.open(pgnfile, "rU"))
             
            # use transaction to avoid autocommit slowness
            trans = self.conn.begin()
            try:
                for i, game in enumerate(cf.games):
                    #print i+1#, cf.get_player_names(i)
                    movelist = array("H")
                    comments = []
                    cf.error = None

                    fenstr = cf._getTag(i, "FEN")
                    variant = cf.get_variant(i)

                    # Fixes for some non statndard Chess960 .pgn
                    if variant==0 and (fenstr is not None) and "Chess960" in cf._getTag(i,"Event"):
                        cf.tagcache[i]["Variant"] = "Fischerandom"
                        variant = 1
                        parts = fenstr.split()
                        parts[0] = parts[0].replace(".", "/").replace("0", "")
                        if len(parts) == 1:
                            parts.append("w")
                            parts.append("-")
                            parts.append("-")
                        fenstr = " ".join(parts)
                    
                    if variant:
                        board = LBoard(FISCHERRANDOMCHESS)
                    else:
                        board = LBoard()

                    if fenstr:
                        try:
                            board.applyFen(fenstr)
                        except SyntaxError as e:
                            print(_("The game #%s can't be loaded, because of an error parsing FEN") % (i+1), e.args[0])
                            continue
                    else:
                        board = LBoard_FEN_START.clone()

                    boards = [board]
                    movetext = cf.get_movetext(i)
                    boards = cf.parse_string(movetext, boards[0], -1)

                    if cf.error is not None:
                        print("ERROR in game #%s" % (i+1), cf.error.args[0])
                        continue

                    walk(boards[0], movelist, comments)
                    
                    if not movelist:
                        if (not comments) and (cf._getTag(i, 'White') is None) and (cf._getTag(i, 'Black') is None):
                            print("empty game")
                            continue
                    
                    event_id = self.get_id(cf._getTag(i, 'Event'), event, EVENT)

                    site_id = self.get_id(cf._getTag(i, 'Site'), site, SITE)

                    game_date = cf._getTag(i, 'Date')
                    if game_date and not '?' in game_date:
                        ymd = game_date.split('.')
                        if len(ymd) == 3:
                            game_year, game_month, game_day = map(int, ymd)
                        else:
                            game_year, game_month, game_day = int(game_date[:4]), None, None
                    elif game_date and not '?' in game_date[:4]:
                        game_year, game_month, game_day = int(game_date[:4]), None, None
                    else:
                        game_year, game_month, game_day = None, None, None

                    game_round = cf._getTag(i, 'Round')

                    white, black = cf.get_player_names(i)
                    white_id = self.get_id(white, player, PLAYER)
                    black_id = self.get_id(black, player, PLAYER)

                    result = cf.get_result(i)
     
                    white_elo = cf._getTag(i, 'WhiteElo')
                    white_elo = int(white_elo) if white_elo and white_elo.isdigit() else None
                    
                    black_elo = cf._getTag(i, 'BlackElo')
                    black_elo = int(black_elo) if black_elo and black_elo.isdigit() else None
     
                    ply_count = cf._getTag(i, "PlyCount")
     
                    event_date = cf._getTag(i, 'EventDate')
     
                    eco = cf._getTag(i, "ECO")
                    eco = eco[:3] if eco else None

                    fen = cf._getTag(i, "FEN")
     
                    variant = cf.get_variant(i)
                    
                    board = cf._getTag(i, "Board")
                    
                    annotator = cf._getTag(i, "Annotator")
                    annotator_id = self.get_id(annotator, annotator, ANNOTATOR)

                    collection_id = self.get_id(unicode(pgnfile), collection, COLLECTION)

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
                        'board': board,
                        'annotator_id': annotator_id,
                        'collection_id': collection_id,
                        'movelist': movelist.tostring(),
                        'comments': unicode("|".join(comments)),
                        })

                    if len(self.game_data) >= CHUNK:
                        if self.collection_data:
                            self.conn.execute(self.ins_collection, self.collection_data)
                            self.collection_data = []

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

                        self.conn.execute(self.ins_game, self.game_data)
                        self.game_data = []
                        print(pgnfile, i+1)
                    
                if self.collection_data:
                    self.conn.execute(self.ins_collection, self.collection_data)
                    self.collection_data = []

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

                if self.game_data:
                    self.conn.execute(self.ins_game, self.game_data)
                    self.game_data = []

                print(pgnfile, i+1)
                trans.commit()

            except ProgrammingError as e:
                trans.rollback()
                print("Importing %s failed! %s" % (file, e))

    def import_FIDE_players(self):
        #print 'drop index'
        #idx = Index('ix_player_name', player.c.name)
        #self.conn.execute(DropIndex(idx))
        #print 'import FIDE players'
        #import_players()
        #print 'create index'
        #idx = Index('ix_player_name', player.c.name)
        #idx.create(engine)

        ins_player = player.insert()
        player_data = []
        with open("players_list.txt") as f:
            # use transaction to avoid autocommit slowness
            trans = self.conn.begin()
            try:
                for i, line in enumerate(f):
                    if i==0:
                        continue

                    elo = line[53:58].rstrip()
                    elo = int(elo) if elo else None
                    
                    born = line[64:68].rstrip()
                    born = int(born) if born else None
                    
                    title = line[44:46].rstrip()
                    title = title if title else None
                    
                    player_data.append({
                        "fideid": int(line[:8]),
                        "name": line[10:42].rstrip(),
                        "title": title,
                        "fed": line[48:51],
                        "elo": elo,
                        "born": born,
                        })

                    if len(player_data) >= CHUNK:
                        self.conn.execute(ins_player, player_data)
                        player_data = []
                        print(i)

                if player_data:
                    self.conn.execute(ins_player, player_data)

                print(i+1)
                trans.commit()

            except:
                trans.rollback()
                raise

    def print_db(self):
        a1 = event.alias()
        a2 = site.alias()
        a3 = player.alias()
        a4 = player.alias()

        s = select([game.c.id, a1.c.name.label('event'), a2.c.name.label('site'), a3.c.name.label('white'), a4.c.name.label('black'),
                    game.c.date_year, game.c.date_month, game.c.date_day, game.c.eco,
                    game.c.result, game.c.white_elo, game.c.black_elo],
                    and_(
                    game.c.event_id==a1.c.id,
                    game.c.site_id==a2.c.id,
                    game.c.white_id==a3.c.id,
                    game.c.black_id==a4.c.id)).where(and_(a3.c.name.startswith(unicode("Réti")), a4.c.name.startswith(unicode("Van Nüss"))))
                     
        result = self.conn.execute(s)
        games = result.fetchall()
        for g in games:
            print("%s %s %s %s %s %s %s %s %s %s %s %s" % (g['id'], g['event'], g['site'], g['white'], g['black'],
                g[5], g[6], g[7], g['eco'], reprResult[g['result']], g['white_elo'], g['black_elo']))


if __name__ == "__main__":
    if 1:
        metadata.drop_all(engine)
        metadata.create_all(engine)

    imp = PgnImport()
    
    from .timer import Timer
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
            imp.do_import(os.path.join('../../../testing/gamefiles', "annotated.pgn"))
            imp.do_import(os.path.join('../../../testing/gamefiles', "world_matches.pgn"))
            imp.do_import(os.path.join('../../../testing/gamefiles', "dortmund.pgn"))
            imp.do_import(os.path.join('../../../testing/gamefiles', "twic923.pgn"))
        print("Elapsed time (secs): %s" % t.elapsed_secs)
        print("Old: 28.68")
    imp.print_db()

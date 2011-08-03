# -*- coding: utf-8 -*-

import os
import sys
from datetime import date
from array import array

#from profilehooks import profile

from sqlalchemy import select, func, and_
from sqlalchemy.exc import ProgrammingError

from pychess.Utils.const import *
from pychess.Savers.pgn import load as pgn_load
from pychess.Savers.database import walk as database_walk
from pychess.Database.model import engine, metadata, event, site, player, game

CHUNK = 1000

EVENT, SITE, PLAYER = range(3)


class PgnImport():
    def __init__(self):
        self.ins_event = event.insert()
        self.ins_site = site.insert()
        self.ins_player = player.insert()
        self.ins_game = game.insert()
        
        self.event_dict = {}
        self.site_dict = {}
        self.player_dict = {}

        self.next_id = [0, 0, 0]

    def get_id(self, name, name_dict, name_data, field):
        if not name:
            return None

        if name in name_dict:
            return name_dict[name]
        else:
            name_data.append({'name': name})
            name_dict[name] = self.next_id[field]
            self.next_id[field] += 1
            return name_dict[name]

    def ini_names(self, name_table, name_dict):
        s = select([name_table])
        name_dict = dict([(n.name, n.id) for n in conn.execute(s)])
        
        s = select([func.max(name_table.c.id).label('maxid')])
        maxid = conn.execute(s).scalar()
        if maxid is None:
            next_id = 1
        else:
            next_id = maxid + 1

        return next_id

    #@profile
    def do_import(self, file, conn):
        # collect new names not in they dict yet
        self.event_data = []
        self.site_data = []
        self.player_data = []
        
        # collect new games and commit them in big chunks for speed
        self.game_data = []

        cf = pgn_load(open(file))
        
        self.next_id[EVENT] = self.ini_names(event, self.event_dict)
        self.next_id[SITE] = self.ini_names(site, self.site_dict)
        self.next_id[PLAYER] = self.ini_names(player, self.player_dict)
        
        # use transaction to avoid autocommit slowness
        trans = conn.begin()
        try:
            for i, game in enumerate(cf.games):
                print i
                game_event = self.get_id(cf._getTag(i, 'Event'), self.event_dict, self.event_data, EVENT)

                game_site = self.get_id(cf._getTag(i, 'Site'), self.site_dict, self.site_data, SITE)

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
                white = self.get_id(white, self.player_dict, self.player_data, PLAYER)
                black = self.get_id(black, self.player_dict, self.player_data, PLAYER)

                result = cf.get_result(i)
 
                white_elo = cf._getTag(i, 'WhiteElo')
                white_elo = int(white_elo) if white_elo else None
                
                black_elo = cf._getTag(i, 'BlackElo')
                black_elo = int(black_elo) if black_elo else None
 
                ply_count = cf._getTag(i, "PlyCount")
 
                event_date = cf._getTag(i, 'EventDate')
 
                eco = cf._getTag(i, "ECO")
                eco = eco[:3] if eco else None

                fen = cf._getTag(i, "FEN")
 
                variant = cf.get_variant(i)
                
                board = cf._getTag(i, "Board")
                
                annotator = cf._getTag(i, "Annotator")
                annotator = self.get_id(annotator, self.player_dict, self.player_data, PLAYER)

                model = cf.loadToModel(i, quick_parse=False)

                movelist = array("h")
                comments = []
                database_walk(model.boards[0], movelist, comments)
                
                if len(self.game_data) < CHUNK:
                    self.game_data.append({
                        'event_id': game_event,
                        'site_id': game_site,
                        'date_year': game_year,
                        'date_month': game_month,
                        'date_day': game_day,
                        'round': game_round,
                        'white_id': white,
                        'black_id': black,
                        'result': result,
                        'white_elo': white_elo,
                        'black_elo': black_elo,
                        'ply_count': ply_count,
                        'eco': eco,
                        'fen': fen,
                        'variant': variant,
                        'board': board,
                        'annotator_id': annotator,
                        'movelist': movelist.tostring(),
                        'comments': "|".join(comments),
                        })
                else:
                    if self.event_data:
                        conn.execute(self.ins_event, self.event_data)
                        self.event_data = []

                    if self.site_data:
                        conn.execute(self.ins_site, self.site_data)
                        self.site_data = []

                    if self.player_data:
                        conn.execute(self.ins_player, self.player_data)
                        self.player_data = []

                    conn.execute(self.ins_game, self.game_data)
                    self.game_data = []
                    print file, CHUNK
                
            if self.event_data:
                conn.execute(self.ins_event, self.event_data)
                self.event_data = []

            if self.site_data:
                conn.execute(self.ins_site, self.site_data)
                self.site_data = []

            if self.player_data:
                conn.execute(self.ins_player, self.player_data)
                self.player_data = []

            if self.game_data:
                conn.execute(self.ins_game, self.game_data)
                self.game_data = []

            print file, i+1
            trans.commit()

        except ProgrammingError, e:
            trans.rollback()
            print "Importing %s failed! %s" % (file, e)


def print_db(conn):
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
                game.c.black_id==a4.c.id)).where(and_(a3.c.name.startswith(u"Réti"), a4.c.name.startswith(u"Van Nüss")))
                 
    result = conn.execute(s)
    games = result.fetchall()
    for g in games:
        print "%s %s %s %s %s %s %s %s %s %s %s %s" % (g['id'], g['event'], g['site'], g['white'], g['black'],
            g[5], g[6], g[7], g['eco'], reprResult[g['result']], g['white_elo'], g['black_elo'])


if __name__ == "__main__":
    conn = engine.connect()
    
    if 1:
        metadata.drop_all(engine)
        metadata.create_all(engine)

    imp = PgnImport()
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg[-4:].lower() == ".pgn":
            if os.path.isfile(arg):
                imp.do_import(arg, conn)
        elif os.path.exists(arg):
            for file in os.listdir(arg):
                if file[-4:].lower() == ".pgn":
                    imp.do_import(os.path.join(arg, file), conn)
    else:
        path = os.path.abspath(os.path.dirname(__file__))
        #path = "/home/tamas/gbtami-database/lib/pychess/Database"
        imp.do_import(os.path.join(path, '../../../testing/gamefiles', "annotated.pgn"), conn)
        imp.do_import(os.path.join(path, '../../../testing/gamefiles', "dortmund.pgn"), conn)
        imp.do_import(os.path.join(path, '../../../testing/gamefiles', "world_matches.pgn"), conn)
        
    print_db(conn)

# -*- coding: utf-8 -*-

import os
from sqlalchemy import create_engine, MetaData, Table, Column, Sequence, Integer, String, SmallInteger, CHAR, LargeBinary, UnicodeText

from pychess.Utils.const import LOCAL, ARTIFICIAL, REMOTE
from pychess.System.prefix import addUserDataPrefix 

pychess_pdb = os.path.join(addUserDataPrefix("pychess.pdb"))
engine = create_engine("sqlite:///" + pychess_pdb, echo=False)
metadata = MetaData()

event = Table('event', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256))
    )

site = Table('site', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256))
    )

annotator = Table('annotator', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256))
    )

player = Table('player', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256), index=True),
    Column('fideid', Integer),
    Column('fed', CHAR(3)),
    Column('title', CHAR(3)),
    Column('elo', SmallInteger),
    Column('born', Integer),
    )

collection = Table('collection', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256)),
    Column('source', String(256))
    )

game = Table('game', metadata,
    Column('id', Integer, primary_key=True),
    Column('event_id', Integer),
    Column('site_id', Integer),
    Column('date_year', SmallInteger),
    Column('date_month', SmallInteger),
    Column('date_day', SmallInteger),
    Column('round', String(8)),
    Column('white_id', Integer),
    Column('black_id', Integer),
    Column('result', SmallInteger),
    Column('white_elo', SmallInteger),
    Column('black_elo', SmallInteger),
    Column('ply_count', SmallInteger),
    Column('eco', CHAR(3)),
    Column('board', SmallInteger),
    Column('fen', String(128)),
    Column('variant', SmallInteger),
    Column('annotator_id', Integer),
    Column('collection_id', Integer),
    Column('movelist', LargeBinary),
    Column('comments', UnicodeText)
    )

def ini_collection():
    conn = engine.connect()
    new_values = [
        {"id": LOCAL, "name": u"Local game"},
        {"id": ARTIFICIAL, "name": u"Chess engine(s)"},
        {"id": REMOTE, "name": u"ICS game"},
        ]
    conn.execute(collection.insert(), new_values)
    conn.close()
    
if not os.path.isfile(pychess_pdb):
    metadata.create_all(engine)
    ini_collection()

# -*- coding: utf-8 -*-

import os
from sqlalchemy import create_engine, MetaData, Table, Column, Sequence, Integer, String, SmallInteger, CHAR, LargeBinary, UnicodeText

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

player = Table('player', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256)),
    Column('fideid', Integer)
    )

game = Table('game', metadata,
    Column('id', Integer, primary_key=True),
    Column('event_id', Integer),
    Column('site_id', Integer),
    Column('date_year', SmallInteger),
    Column('date_month', SmallInteger),
    Column('date_day', SmallInteger),
    Column('round', SmallInteger),
    Column('white_id', Integer),
    Column('black_id', Integer),
    Column('result', SmallInteger),
    Column('white_elo', SmallInteger),
    Column('black_elo', SmallInteger),
    Column('white_title', CHAR(3)),
    Column('black_title', CHAR(3)),
    Column('ply_count', SmallInteger),
    Column('eco', CHAR(3)),
    Column('board', SmallInteger),
    Column('fen', String(128)),
    Column('variant', SmallInteger),
    Column('annotator_id', Integer),
    Column('movelist', LargeBinary),
    Column('comments', UnicodeText)
    )

if not os.path.isfile(pychess_pdb):
    metadata.create_all(engine)


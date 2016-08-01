# -*- coding: utf-8 -*-

import os
from sqlalchemy import create_engine, MetaData, Table, Column, Integer,\
    String, SmallInteger, BigInteger, LargeBinary, UnicodeText, ForeignKey

from pychess.compat import unicode
from pychess.Utils.const import LOCAL, ARTIFICIAL, REMOTE
from pychess.System.prefix import addUserDataPrefix

engine = None


def set_engine(url, echo=False):
    global engine
    engine = create_engine(url, echo=echo)

metadata = MetaData()

event = Table(
    'event', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256))
)

site = Table(
    'site', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256))
)

annotator = Table(
    'annotator', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256))
)

player = Table(
    'player', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256), index=True),
    Column('fideid', Integer),
    Column('fed', String(3)),
    Column('title', String(3)),
    Column('elo', SmallInteger),
    Column('born', Integer),
)

pl1 = player.alias()
pl2 = player.alias()

game = Table(
    'game', metadata,
    Column('id', Integer, primary_key=True),
    Column('event_id', Integer, ForeignKey('event.id')),
    Column('site_id', Integer, ForeignKey('site.id')),
    Column('date_year', SmallInteger),
    Column('date_month', SmallInteger),
    Column('date_day', SmallInteger),
    Column('round', String(8)),
    Column('white_id', Integer, ForeignKey('player.id')),
    Column('black_id', Integer, ForeignKey('player.id')),
    Column('result', SmallInteger),
    Column('white_elo', SmallInteger),
    Column('black_elo', SmallInteger),
    Column('ply_count', SmallInteger),
    Column('eco', String(3)),
    Column('time_control', String(7)),
    Column('board', SmallInteger),
    Column('fen', String(128)),
    Column('variant', SmallInteger),
    Column('termination', SmallInteger),
    Column('annotator_id', Integer, ForeignKey('annotator.id')),
    Column('movelist', LargeBinary),
    Column('comments', UnicodeText)
)

# bitboards stored as bb - 2**63 + 1 to fit into sqlite (8 byte) signed(!) integer range
bitboard = Table(
    'bitboard', metadata,
    Column('id', Integer, primary_key=True),
    Column('game_id', Integer, ForeignKey('game.id'), nullable=False),
    Column('ply', Integer),
    Column('bitboard', BigInteger),
)

tag = Table(
    'tag', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256)),
)

tag_game = Table(
    'tags', metadata,
    Column('id', Integer, primary_key=True),
    Column('game_id', Integer, ForeignKey('game.id'), nullable=False),
    Column('tag_id', Integer, ForeignKey('tag.id'), nullable=False),
)


def ini_tag():
    conn = engine.connect()
    new_values = [
        {"id": LOCAL, "name": unicode("Local game")},
        {"id": ARTIFICIAL, "name": unicode("Chess engine(s)")},
        {"id": REMOTE, "name": unicode("ICS game")},
    ]
    conn.execute(tag.insert(), new_values)
    conn.close()

pychess_pdb = os.path.join(addUserDataPrefix("pychess.pdb"))
set_engine("sqlite:///" + pychess_pdb)  # , echo=True)
if not os.path.isfile(pychess_pdb):
    metadata.create_all(engine)
    ini_tag()

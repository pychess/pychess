# -*- coding: utf-8 -*-

import os
import time

from sqlalchemy import create_engine, MetaData, Table, Column, Integer,\
    String, SmallInteger, BigInteger, LargeBinary, UnicodeText, ForeignKey, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import Executable, ClauseElement, _literal_as_text

from pychess.compat import unicode
from pychess.Utils.const import LOCAL, ARTIFICIAL, REMOTE
from pychess.System.prefix import addUserDataPrefix
from pychess.System import conf
from pychess.System.Log import log


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()
    log.debug("Start Query:\n%s" % statement, extra={"task": "SQL"})
    log.debug("Parameters:\n%r" % (parameters,), extra={"task": "SQL"})


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    log.debug("Query Complete!", extra={"task": "SQL"})
    log.debug("Total Time: %.02fms" % (total * 1000), extra={"task": "SQL"})


class Explain(Executable, ClauseElement):
    def __init__(self, stmt):
        self.statement = _literal_as_text(stmt)


@compiles(Explain, 'sqlite')
def slite_explain(element, compiler, **kw):
    text = "EXPLAIN QUERY PLAN "
    text += compiler.process(element.statement, **kw)
    return text


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    # www.sqlite.org/pragma.html
    cursor.execute("PRAGMA page_size = 4096")
    cursor.execute("PRAGMA cache_size=10000")
    # cursor.execute("PRAGMA locking_mode=EXCLUSIVE")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA journal_mode=WAL")
    # cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

engines = {}


# If we use sqlite as db backend we have to store bitboards as
# bb - DB_MAXINT_SHIFT to fit into sqlite (8 byte) signed(!) integer range
DB_MAXINT_SHIFT = 2**63 - 1


def get_engine(path=None, dialect="sqlite", echo=False):
    global DB_MAXINT_SHIFT

    if path is None:
        url = "sqlite://"
    elif dialect == "sqlite":
        url = "%s:///%s" % (dialect, path)
    else:
        DB_MAXINT_SHIFT = 0
        # TODO: embedded firebird/mysql

    if url in engines:
        return engines[url]
    else:
        if path is None:
            engine = create_engine(url, connect_args={'check_same_thread': False},
                                   echo=echo, poolclass=StaticPool)
        else:
            engine = create_engine(url, echo=echo)

        if path is None or not os.path.isfile(path):
            metadata.create_all(engine)
            ini_tag(engine)
        engines[url] = engine
        return engine


metadata = MetaData()

source = Table(
    'source', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256)),
    Column('info', String(256))
)

event = Table(
    'event', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256), index=True)
)

site = Table(
    'site', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256), index=True)
)

annotator = Table(
    'annotator', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256), index=True)
)

player = Table(
    'player', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256), index=True),
    Column('fideid', String(14), index=True, unique=True),
    Column('fed', String(3)),
    Column('sex', String(1)),
    Column('title', String(3)),
    Column('elo', SmallInteger),
    Column('born', Integer),
)

pl1 = player.alias()
pl2 = player.alias()

game = Table(
    'game', metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('event_id', Integer, ForeignKey('event.id'), index=True),
    Column('site_id', Integer, ForeignKey('site.id'), index=True),
    Column('date_year', SmallInteger),
    Column('date_month', SmallInteger),
    Column('date_day', SmallInteger),
    Column('round', String(8)),
    Column('white_id', Integer, ForeignKey('player.id'), index=True),
    Column('black_id', Integer, ForeignKey('player.id'), index=True),
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
    Column('annotator_id', Integer, ForeignKey('annotator.id'), index=True),
    Column('source_id', Integer, ForeignKey('source.id'), index=True),
    Column('movelist', LargeBinary),
    Column('comments', UnicodeText)
)

bitboard = Table(
    'bitboard', metadata,
    Column('id', Integer, primary_key=True),
    Column('game_id', Integer, ForeignKey('game.id'), nullable=False),
    Column('ply', Integer, index=True),
    Column('bitboard', BigInteger, index=True),
)

tag = Table(
    'tag', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256), index=True),
)

tag_game = Table(
    'tags', metadata,
    Column('id', Integer, primary_key=True),
    Column('game_id', Integer, ForeignKey('game.id'), nullable=False),
    Column('tag_id', Integer, ForeignKey('tag.id'), nullable=False, index=True),
)


def drop_indexes(engine):
    for table in metadata.tables.values():
        for index in table.indexes:
            try:
                index.drop(bind=engine)
            except OperationalError as e:
                if e.orig.args[0].startswith("no such index"):
                    print(e.orig.args[0])
                else:
                    raise


def create_indexes(engine):
    for table in metadata.tables.values():
        for index in table.indexes:
            index.create(bind=engine)


def ini_tag(engine):
    conn = engine.connect()
    new_values = [
        {"id": LOCAL, "name": unicode("Local game")},
        {"id": ARTIFICIAL, "name": unicode("Chess engine(s)")},
        {"id": REMOTE, "name": unicode("ICS game")},
    ]
    conn.execute(tag.insert(), new_values)
    conn.close()

pychess_pdb = os.path.join(addUserDataPrefix("pychess.pdb"))
pychess_pdb = conf.get("autosave_db_file", pychess_pdb)

get_engine(None)  # in memory clipbase
get_engine(pychess_pdb)

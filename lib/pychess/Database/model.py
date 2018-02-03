# -*- coding: utf-8 -*-

import os
import shutil
import time

from sqlalchemy import create_engine, MetaData, Table, Column, Integer,\
    String, SmallInteger, ForeignKey, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import Executable, ClauseElement, _literal_as_text

from pychess.Utils.const import LOCAL, ARTIFICIAL, REMOTE
from pychess.System.Log import log
from pychess.System.prefix import addUserCachePrefix


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


# Just to make sphinx happy...
try:
    class Explain(Executable, ClauseElement):
        def __init__(self, stmt):
            self.statement = _literal_as_text(stmt)
except TypeError:
    class Explain:
        pass


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
    # cursor.execute("PRAGMA journal_mode=WAL")
    # cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def insert_or_ignore(engine, stmt):
    if engine.name == "sqlite":
        # can't use "OR UPDATE" because it delete+insert records
        # and breaks referential integrity
        return stmt.prefix_with("OR IGNORE")
    elif engine.name == "postgresql":
        return stmt.prefix_with("ON CONFLICT DO NOTHING")
    elif engine.name == "mysql":
        return stmt.prefix_with("IGNORE")


engines = {}

# PyChess database schema version
SCHEMA_VERSION = "20170109"


def get_engine(path=None, dialect="sqlite", echo=False):
    if path is None:
        url = "sqlite://"
    elif dialect == "sqlite":
        url = "%s:///%s" % (dialect, path)

    if url in engines and os.path.isfile(path) and os.path.getsize(path) > 0:
        return engines[url]
    else:
        if path is None:
            engine = create_engine(url, connect_args={'check_same_thread': False},
                                   echo=echo, poolclass=StaticPool)
        else:
            if path != empty_db and (not os.path.isfile(path) or os.path.getsize(path) == 0):
                shutil.copyfile(empty_db, path)
            engine = create_engine(url, echo=echo)

        if path is None or not os.path.isfile(path):
            metadata.create_all(engine)
            ini_tag(engine)
            ini_schema_version(engine)

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
)

pl1 = player.alias()
pl2 = player.alias()

game = Table(
    'game', metadata,
    Column('id', Integer, primary_key=True, index=True),
    Column('offset', Integer, index=True),
    Column('offset8', Integer, index=True),
    Column('event_id', Integer, ForeignKey('event.id'), index=True),
    Column('site_id', Integer, ForeignKey('site.id'), index=True),
    Column('date_year', SmallInteger),
    Column('date_month', SmallInteger),
    Column('date_day', SmallInteger),
    Column('round', String(8), default=""),
    Column('white_id', Integer, ForeignKey('player.id'), index=True),
    Column('black_id', Integer, ForeignKey('player.id'), index=True),
    Column('result', SmallInteger, default=0),
    Column('white_elo', SmallInteger, default=0),
    Column('black_elo', SmallInteger, default=0),
    Column('ply_count', SmallInteger, default=0),
    Column('eco', String(3), default=""),
    Column('time_control', String(7), default=""),
    Column('board', SmallInteger, default=0),
    Column('fen', String(128), default=""),
    Column('variant', SmallInteger, default=0),
    Column('termination', SmallInteger, default=0),
    Column('annotator_id', Integer, ForeignKey('annotator.id'), index=True),
    Column('source_id', Integer, ForeignKey('source.id'), index=True),
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

schema_version = Table(
    'schema_version', metadata,
    Column('id', Integer, primary_key=True),
    Column('version', String(8)),
)


def drop_indexes(engine):
    for table in metadata.tables.values():
        for index in table.indexes:
            try:
                index.drop(bind=engine)
            except OperationalError as e:
                if e.orig.args[0].startswith("no such index"):
                    pass
                    # print(e.orig.args[0])
                else:
                    raise


def create_indexes(engine):
    for table in metadata.tables.values():
        for index in table.indexes:
            index.create(bind=engine)


def ini_tag(engine):
    conn = engine.connect()
    new_values = [
        {"id": LOCAL, "name": "Local game"},
        {"id": ARTIFICIAL, "name": "Chess engine(s)"},
        {"id": REMOTE, "name": "ICS game"},
    ]
    conn.execute(tag.insert(), new_values)
    conn.close()


def ini_schema_version(engine):
    conn = engine.connect()
    conn.execute(schema_version.insert(), [
        {"id": 1, "version": SCHEMA_VERSION},
    ])
    conn.close()


# create an empty database to use as skeleton
empty_db = os.path.join(addUserCachePrefix("%s.sqlite" % SCHEMA_VERSION))
if not os.path.isfile(empty_db):
    engine = get_engine(empty_db)
    engine.dispose()

# -*- coding: UTF-8 -*-


from sqlalchemy import select, func, and_, or_

from pychess.Utils.const import FEN_START, WHITE, BLACK, reprResult
from pychess.Database import model as dbmodel
from pychess.Database.model import game, event, site, player, pl1, pl2, annotator, source


count_games = select([func.count()]).select_from(game)


def save(path, model, offset):
    game_event = model.tags["Event"]
    game_site = model.tags["Site"]

    year, month, day = int(model.tags["Year"]), int(model.tags["Month"]), int(model.tags["Day"])
    game_round = model.tags.get("Round")

    white = repr(model.players[WHITE])
    black = repr(model.players[BLACK])

    result = model.status
    eco = model.tags.get("ECO")

    time_control = model.tags.get("TimeControl")
    board = int(model.tags.get("Board")) if model.tags.get("Board") else None

    white_elo = int(model.tags.get("WhiteElo")) if model.tags.get("WhiteElo") else None
    black_elo = int(model.tags.get("BlackElo")) if model.tags.get("BlackElo") else None

    variant = model.variant.variant

    fen = model.boards[0].board.asFen()
    fen = fen if fen != FEN_START else None

    game_annotator = model.tags.get("Annotator")
    ply_count = model.ply - model.lowply

    def get_id(table, name):
        if not name:
            return None

        selection = select([table.c.id], table.c.name == name)
        result = conn.execute(selection)
        id_ = result.scalar()
        if id_ is None:
            result = conn.execute(table.insert().values(name=name))
            id_ = result.inserted_primary_key[0]
        return id_

    engine = dbmodel.get_engine(path)

    conn = engine.connect()
    trans = conn.begin()
    try:
        event_id = get_id(event, game_event)
        site_id = get_id(site, game_site)
        white_id = get_id(player, white)
        black_id = get_id(player, black)
        annotator_id = get_id(annotator, game_annotator)

        new_values = {
            'offset': offset,
            'offset8': (offset >> 3) << 3,
            'event_id': event_id,
            'site_id': site_id,
            'date_year': year,
            'date_month': month,
            'date_day': day,
            'round': game_round,
            'white_id': white_id,
            'black_id': black_id,
            'result': result,
            'white_elo': white_elo,
            'black_elo': black_elo,
            'ply_count': ply_count,
            'eco': eco,
            'time_control': time_control,
            'board': board,
            'fen': fen,
            'variant': variant,
            'annotator_id': annotator_id,
        }

        if hasattr(model, "game_id") and model.game_id is not None:
            result = conn.execute(game.update().where(
                game.c.id == model.game_id).values(new_values))
        else:
            result = conn.execute(game.insert().values(new_values))
            model.game_id = result.inserted_primary_key[0]

        trans.commit()
    except:
        trans.rollback()
        raise
    conn.close()


class TagDatabase:
    def __init__(self, engine):
        self.engine = engine

        self.cols = [
            game.c.id.label("Id"), game.c.offset.label("Offset"),
            game.c.offset8.label("Offset8"), pl1.c.name.label('White'),
            pl2.c.name.label('Black'), game.c.result.label('Result'),
            event.c.name.label('Event'), site.c.name.label('Site'),
            game.c.round.label('Round'), game.c.date_year.label('Year'),
            game.c.date_month.label('Month'), game.c.date_day.label('Day'),
            game.c.white_elo.label('WhiteElo'), game.c.black_elo.label('BlackElo'),
            game.c.ply_count.label('PlyCount'), game.c.eco.label('ECO'),
            game.c.time_control.label('TimeControl'), game.c.fen.label('Board'),
            game.c.fen.label('FEN'), game.c.variant.label('Variant'),
            annotator.c.name.label('Annotator')]

        self.from_obj = [
            game.outerjoin(pl1, game.c.white_id == pl1.c.id)
            .outerjoin(pl2, game.c.black_id == pl2.c.id)
            .outerjoin(event, game.c.event_id == event.c.id)
            .outerjoin(site, game.c.site_id == site.c.id)
            .outerjoin(annotator, game.c.annotator_id == annotator.c.id)]

        self.select = select(self.cols, from_obj=self.from_obj)

        self.select_offsets = select([game.c.offset, ], from_obj=self.from_obj)

        self.colnames = self.engine.execute(self.select).keys()

        self.query = self.select
        self.orderby = None
        self.where_tags = None
        self.where_offs = None
        self.where_offs8 = None

    def get_count(self):
        return self.engine.execute(count_games).scalar()
    count = property(get_count)

    def close(self):
        self.engine.dispose()

    def build_where_tags(self, tag_query):
        if tag_query is not None:
            tags = []
            if "white" in tag_query:
                if "ignore_tag_colors" in tag_query:
                    tags.append(or_(pl1.c.name.startswith(tag_query["white"]),
                                    pl2.c.name.startswith(tag_query["white"])))
                else:
                    tags.append(pl1.c.name.startswith(tag_query["white"]))

            if "black" in tag_query:
                if "ignore_tag_colors" in tag_query:
                    tags.append(or_(pl1.c.name.startswith(tag_query["black"]),
                                    pl2.c.name.startswith(tag_query["black"])))
                else:
                    tags.append(pl2.c.name.startswith(tag_query["black"]))

            if "event" in tag_query:
                tags.append(event.c.name.startswith(tag_query["event"])),

            if "site" in tag_query:
                tags.append(site.c.name.startswith(tag_query["site"])),

            if "eco_from" in tag_query:
                tags.append(game.c.eco >= tag_query["eco_from"])

            if "eco_to" in tag_query:
                tags.append(game.c.eco <= tag_query["eco_to"])

            if "annotator" in tag_query:
                tags.append(annotator.c.name.startswith(tag_query["annotator"])),

            if "result" in tag_query:
                tags.append(game.c.result == reprResult.index(tag_query["result"])),

            if "year_from" in tag_query:
                tags.append(game.c.date_year >= tag_query["year_from"])

            if "year_to" in tag_query:
                tags.append(game.c.date_year <= tag_query["year_to"])

            if "elo_from" in tag_query:
                tags.append(game.c.white_elo >= tag_query["elo_from"])
                tags.append(game.c.black_elo >= tag_query["elo_from"])

            if "elo_to" in tag_query:
                tags.append(game.c.white_elo <= tag_query["elo_to"])
                tags.append(game.c.black_elo <= tag_query["elo_to"])

            self.where_tags = and_(*tags)
        else:
            self.where_tags = None

    def build_where_offs8(self, offset_list):
        if offset_list is not None and len(offset_list) > 0:
            self.where_offs8 = game.c.offset8.in_(offset_list)
        else:
            self.where_offs8 = None

    def build_where_offs(self, offset_list):
        if offset_list is not None and len(offset_list) > 0:
            self.where_offs = game.c.offset.in_(offset_list)
        else:
            self.where_offs = None

    def build_query(self):
        self.query = self.select

        if self.where_tags is not None:
            self.query = self.query.where(self.where_tags)

        if self.where_offs8 is not None:
            self.query = self.query.where(self.where_offs8)

        if self.where_offs is not None:
            self.query = self.query.where(self.where_offs)

    def get_records(self, last_seen_offs, limit):
        self.build_query()

        # we use .where() to implement pagination because .offset() doesn't scale on big tables
        query = self.query.where(game.c.offset > last_seen_offs).order_by(game.c.offset).limit(limit)

        # log.debug(self.engine.execute(Explain(query)).fetchall(), extra={"task": "SQL"})

        result = self.engine.execute(query)
        records = result.fetchall()

        return records

    def get_offsets_for_tags(self, last_seen_offs):
        query = self.select_offsets.where(self.where_tags).where(game.c.offset > last_seen_offs)
        result = self.engine.execute(query)
        return [rec[0] for rec in result.fetchall()]

    def get_info(self, rec):
        where = and_(game.c.source_id == source.c.id, game.c.id == rec["Id"])
        result = self.engine.execute(select([source.c.info]).where(where)).first()

        if result is None:
            return None
        else:
            return result[0]

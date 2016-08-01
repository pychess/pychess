# -*- coding: UTF-8 -*-

from __future__ import absolute_import
from __future__ import print_function

from array import array

from sqlalchemy import select, func, or_, and_

from pychess.compat import unicode
from pychess.Savers.pgn import PGNFile
from pychess.Utils.const import reprResult, WHITE, BLACK
from pychess.Utils.const import FEN_START
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Database import model as dbmodel
from pychess.Database.dbwalk import walk, COMMENT, VARI_START, VARI_END, NAG
from pychess.Database.model import game, event, site, player, pl1, pl2, annotator, bitboard
from pychess.Variants import variants
from pychess.System import Timer

__label__ = _("PyChess database")
__ending__ = "pdb"
__append__ = True


def save(file, model, position=None):
    movelist = array("H")
    comments = []
    walk(model.boards[0].board, movelist, comments)

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

    conn = dbmodel.engine.connect()
    trans = conn.begin()
    try:
        event_id = get_id(event, game_event)
        site_id = get_id(site, game_site)
        white_id = get_id(player, white)
        black_id = get_id(player, black)
        annotator_id = get_id(annotator, game_annotator)

        new_values = {
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
            'movelist': movelist.tostring(),
            'comments': "|".join(comments),
        }

        if hasattr(model, "game_id") and model.game_id is not None:
            result = conn.execute(game.update().where(
                game.c.id == model.game_id).values(new_values))

            result = conn.execute(bitboard.delete().where(
                bitboard.c.game_id == model.game_id))
        else:
            result = conn.execute(game.insert().values(new_values))
            game_id = model.game_id = result.inserted_primary_key[0]

            if not fen:
                bitboard_data = []
                # store one bitboard for all ply to help  opening tree lookups
                # bitboards stored as bb - 2**63 + 1 to fit into sqlite (8 byte) signed(!) integer range
                for ply, board in enumerate(model.boards):
                    bb = board.board.friends[0] | board.board.friends[1]
                    bitboard_data.append({
                        'game_id': game_id,
                        'ply': ply,
                        'bitboard': bb - 2**63 + 1,
                    })
                result = conn.execute(bitboard.insert(), bitboard_data)

        trans.commit()
    except:
        trans.rollback()
        raise


def load(file):
    return Database(file, [])


class Database(PGNFile):
    def __init__(self, file, games):
        PGNFile.__init__(self, file, games)

        self.cols = [
            game.c.id.label("Id"), pl1.c.name.label('White'),
            pl2.c.name.label('Black'), game.c.result.label('Result'),
            event.c.name.label('Event'), site.c.name.label('Site'),
            game.c.round.label('Round'), game.c.date_year.label('Year'),
            game.c.date_month.label('Month'), game.c.date_day.label('Day'),
            game.c.white_elo.label('WhiteElo'), game.c.black_elo.label('BlackElo'),
            game.c.ply_count.label('PlyCount'), game.c.eco.label('ECO'), game.c.fen.label('Board'),
            game.c.time_control.label('TC'),
            game.c.fen.label('FEN'), game.c.variant.label('Variant'),
            annotator.c.name.label('Annotator')]

        self.from_obj0 = [
            game.outerjoin(pl1, game.c.white_id == pl1.c.id)
            .outerjoin(pl2, game.c.black_id == pl2.c.id)
            .outerjoin(event, game.c.event_id == event.c.id)
            .outerjoin(site, game.c.site_id == site.c.id)
            .outerjoin(annotator, game.c.annotator_id == annotator.c.id)]

        self.from_obj1 = [
            game.outerjoin(pl1, game.c.white_id == pl1.c.id)
            .outerjoin(pl2, game.c.black_id == pl2.c.id)
            .outerjoin(event, game.c.event_id == event.c.id)
            .outerjoin(site, game.c.site_id == site.c.id)
            .outerjoin(annotator, game.c.annotator_id == annotator.c.id)
            .outerjoin(bitboard, bitboard.c.game_id == game.c.id)]

        self.from_obj2 = [game.outerjoin(bitboard, bitboard.c.game_id == game.c.id)]

        self.count = dbmodel.engine.execute(select([func.count()]).select_from(game)).scalar()
        print("Database contains %s games" % self.count)

        self.select0 = select(self.cols, from_obj=self.from_obj0)
        self.select1 = select(self.cols, from_obj=self.from_obj1)

        self.colnames = dbmodel.engine.execute(self.select0).keys()
        # print(self.colnames)

        self.query = self.select0
        self.orderby = None
        self.where_tags = None
        self.where_bitboards = None

    def close(self):
        dbmodel.engine.dispose()

    def build_query(self):
        print("build_query()")
        if self.where_tags is not None and self.where_bitboards is not None:
            self.query = self.select1.where(self.where_tags).where(self.where_bitboards)
        elif self.where_tags is not None:
            self.query = self.select0.where(self.where_tags)
        elif self.where_bitboards is not None:
            self.query = self.select1.where(self.where_bitboards)
        else:
            self.query = self.select0

        if self.orderby is not None:
            self.query = self.query.order_by(self.orderby)

    def update_count(self):
        print("update_count()")
        if self.where_tags is not None and self.where_bitboards is not None:
            stmt = select([func.count()], from_obj=self.from_obj1).where(self.where_tags).where(self.where_bitboards)
            self.count = dbmodel.engine.execute(stmt).scalar()
        elif self.where_tags is not None:
            stmt = select([func.count()], from_obj=self.from_obj0).where(self.where_tags)
            self.count = dbmodel.engine.execute(stmt).scalar()
        elif self.where_bitboards is not None:
            stmt = select([func.count()], from_obj=self.from_obj2).where(self.where_bitboards)
            self.count = dbmodel.engine.execute(stmt).scalar()
        else:
            self.count = self.count

        print("%s game(s) match to query" % self.count)

    def build_where_tags(self, text):
        print("build_where_tags()")
        if text:
            text = unicode(text)
            self.where_tags = or_(
                pl1.c.name.contains(text),
                pl2.c.name.contains(text),
                event.c.name.contains(text),
                site.c.name.contains(text),
                annotator.c.name.contains(text),
            )
        else:
            self.where_tags = None

    def build_where_bitboards(self, ply, bb):
        print("build_where_bitboards()")
        if ply:
            self.where_bitboards = and_(bitboard.c.game_id == game.c.id, bitboard.c.ply == ply, bitboard.c.bitboard == bb)
        else:
            self.where_bitboars = None

    def get_records(self, offset, limit):
        with Timer(True):
            query = self.query.offset(offset).limit(limit)
            print(query)
            result = dbmodel.engine.execute(query)
            self.games = result.fetchall()

    def get_id(self, gameno):
        return self.games[gameno]["Id"]

    def get_movetext(self, gameno):
        selection = select([game.c.movelist, game.c.comments],
                           game.c.id == self.games[gameno][0])
        result = dbmodel.engine.execute(selection).first()
        self.comments = result[1].split("|")
        arr = array("H")
        arr.fromstring(result[0])
        return arr

    def get_bitboards(self, ply, prev_bb=None):
        with Timer(True):
            if prev_bb is not None:
                stmt = select([bitboard.c.game_id]).where(bitboard.c.bitboard == prev_bb)
                where = and_(bitboard.c.ply == ply, bitboard.c.game_id.in_(stmt))
            else:
                where = bitboard.c.ply == ply
            sel = select([bitboard.c.bitboard, func.count(bitboard.c.bitboard)]).group_by(bitboard.c.bitboard).where(where)
            print(sel)
            return dbmodel.engine.execute(sel).fetchall()

    def loadToModel(self, gameno, position=-1, model=None):
        self.comments = []
        self.comment_idx = 0
        model = PGNFile.loadToModel(self,
                                    gameno,
                                    position=position,
                                    model=model)
        model.game_id = self.games[gameno]["Id"]
        return model

    def _getTag(self, gameno, tagkey):
        if tagkey == "Result":
            return reprResult[self.games[gameno][tagkey]]

        elif tagkey == "Date":
            year = self.games[gameno]['Year']
            month = self.games[gameno]['Month']
            day = self.games[gameno]['Day']
            tag_date = "%s.%s.%s" % (year if year else "????", month if month else "??", day
                                     if day else "??")
            return tag_date

        elif tagkey == "Variant":
            variant = self.games[gameno]['Variant']
            return variants[variant].cecp_name.capitalize() if variant else ""

        elif tagkey in self.colnames:
            tag = self.games[gameno][tagkey]
            return "%s" % (tag if tag else "")

        else:
            return ""

    def parse_string(self, movetext, board, position, variation=False):
        boards = []

        last_board = board
        if variation:
            # this board used only to hold initial variation comments
            boards.append(LBoard(board.variant))
        else:
            # initial game board
            boards.append(board)

        error = None
        parenthesis = 0
        v_array = array("H")
        v_last_board = None
        for elem in movetext:
            if parenthesis > 0:
                v_array.append(elem)

            if elem == VARI_END:
                parenthesis -= 1
                if parenthesis == 0:
                    v_last_board.children.append(
                        self.parse_string(v_array[:-1],
                                          last_board.prev,
                                          position,
                                          variation=True))
                    v_array = array("H")
                    continue

            elif elem == VARI_START:
                parenthesis += 1
                if parenthesis == 1:
                    v_last_board = last_board

            if parenthesis == 0:
                if elem < COMMENT:
                    # a move
                    if not variation:
                        if position != -1 and last_board.plyCount >= position:
                            break

                    new_board = last_board.clone()
                    new_board.applyMove(elem)

                    new_board.prev = last_board

                    # set last_board next, except starting a new variation
                    if variation and last_board == board:
                        boards[0].next = new_board
                    else:
                        last_board.next = new_board

                    boards.append(new_board)
                    last_board = new_board

                elif elem == COMMENT:
                    comment = self.comments[self.comment_idx]
                    self.comment_idx += 1
                    if variation and last_board == board:
                        # initial variation comment
                        boards[0].children.append(comment)
                    else:
                        last_board.children.append(comment)

                elif elem > NAG:
                    # NAG
                    last_board.nags.append("$%s" % (elem - NAG))

                else:
                    print("Unknown element in movelist array:", elem)

            if error:
                raise error

        return boards

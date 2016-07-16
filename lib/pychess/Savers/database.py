# -*- coding: UTF-8 -*-

from __future__ import absolute_import
from __future__ import print_function

from array import array

from sqlalchemy import select, func, or_

from pychess.compat import unicode
from pychess.Savers.pgn import PGNFile
from pychess.Utils.const import reprResult, WHITE, BLACK
from pychess.Utils.const import FEN_START, REMOTE, ARTIFICIAL, LOCAL
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Database import model as dbmodel
from pychess.Database.dbwalk import walk, COMMENT, VARI_START, VARI_END, NAG
from pychess.Database.model import engine, game, event, site, player, pl1, pl2, annotator, bitboard
from pychess.Variants import variants

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

        white_type = model.players[WHITE].__type__
        black_type = model.players[BLACK].__type__
        if REMOTE in (white_type, black_type):
            collection_id = REMOTE
        elif ARTIFICIAL in (white_type, black_type):
            collection_id = ARTIFICIAL
        else:
            collection_id = LOCAL

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
            'collection_id': collection_id,
            'movelist': movelist.tostring(),
            'comments': "|".join(comments),
        }

        if hasattr(model, "game_id") and model.game_id is not None:
            result = conn.execute(game.update().where(
                game.c.id == model.game_id).values(new_values))
        else:
            result = conn.execute(game.insert().values(new_values))
            model.game_id = result.inserted_primary_key[0]

        # TODO: save bitboards!

        trans.commit()
    except:
        trans.rollback()
        raise


def load(file):
    conn = dbmodel.engine.connect()

    selection = select([func.count(game.c.id)])
    count = conn.execute(selection).scalar()
    print("Database contains %s games" % count)

    selection = select([
        game.c.id.label("Id"), pl1.c.name.label('White'),
        pl2.c.name.label('Black'), game.c.result.label('Result'),
        event.c.name.label('Event'), site.c.name.label('Site'),
        game.c.round.label('Round'), game.c.date_year.label('Year'),
        game.c.date_month.label('Month'), game.c.date_day.label('Day'),
        game.c.white_elo.label('WhiteElo'), game.c.black_elo.label('BlackElo'),
        game.c.ply_count.label('PlyCount'), game.c.eco.label('ECO'), game.c.fen.label('Board'),
        game.c.time_control.label('TC'),
        game.c.fen.label('FEN'), game.c.variant.label('Variant'),
        annotator.c.name.label('Annotator')],
        from_obj=[
            game.outerjoin(pl1, game.c.white_id == pl1.c.id)
            .outerjoin(pl2, game.c.black_id == pl2.c.id)
            .outerjoin(event, game.c.event_id == event.c.id)
            .outerjoin(site, game.c.site_id == site.c.id)
            .outerjoin(annotator, game.c.annotator_id == annotator.c.id)])

    result = conn.execute(selection)
    colnames = result.keys()
    # print(colnames)
    result.close()
    return Database(file, [], colnames, selection, count)


class Database(PGNFile):
    def __init__(self, file, games, colnames, select, count):
        PGNFile.__init__(self, file, games)

        self.conn = engine.connect()

        self.colnames = colnames
        self.select = select
        self.query = None
        self.orderby = None
        self.where = None
        self.count = count

    def close(self):
        self.conn.close()

    def build_query(self):
        self.query = self.select

        if self.where is None:
            self.count = self.count
        else:
            s = select([func.count(game.c.id)], from_obj=[
                game.outerjoin(pl1, game.c.white_id == pl1.c.id)
                .outerjoin(pl2, game.c.black_id == pl2.c.id)])
            self.count = self.conn.execute(s.where(self.where)).scalar()
            self.query = self.query.where(self.where)
        print("%s game(s) match to query" % self.count)

        if self.orderby is not None:
            self.query = self.query.order_by(self.orderby)

    def build_where(self, text):
        if text:
            self.where = or_(pl1.c.name.startswith(unicode(text)), pl2.c.name.startswith(unicode(text)))
        else:
            self.where = None

    def get_records(self, offset, limit):
        query = self.query.offset(offset).limit(limit)
        result = self.conn.execute(query)
        self.games = result.fetchall()

    def get_id(self, gameno):
        return self.games[gameno]["Id"]

    def get_movetext(self, gameno):
        selection = select([game.c.movelist, game.c.comments],
                           game.c.id == self.games[gameno][0])
        conn = dbmodel.engine.connect()
        result = conn.execute(selection).first()
        self.comments = result[1].split("|")
        arr = array("H")
        arr.fromstring(result[0])
        return arr

    def get_bitboards(self, ply):
        sel = select([bitboard.c.bitboard, func.count(bitboard.c.bitboard)]).where(bitboard.c.ply == ply).group_by(bitboard.c.bitboard)
        return self.conn.execute(sel).fetchall()

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
                        if position != -1 and last_board.ply >= position:
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

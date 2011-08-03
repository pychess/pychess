# -*- coding: UTF-8 -*-

from array import array

from sqlalchemy import create_engine, select, insert, and_

from pgn import PGNFile
from pychess.Utils.const import reprResult, WHITE, BLACK
from pychess.Utils.Board import Board
from pychess.Utils.Move import Move
from pychess.Utils.const import *
from pychess.Database.model import engine, metadata, event, site, player, game
from pychess.Variants.fischerandom import FischerRandomChess

__label__ = _("PyChess database")
__endings__ = "pdb",
__append__ = True

COMMENT, VARI_START, VARI_END, NAG = -1, -2, -3, -4


def save (file, model):
    movelist = array("h")
    comments = []
    walk(model.boards[0], movelist, comments)

    game_event = model.tags["Event"]
    game_site = model.tags["Site"]
    year, month, day = int(model.tags["Year"]), int(model.tags["Month"]), int(model.tags["Day"])
    game_round = model.tags.get("Round")
    white = repr(model.players[WHITE])
    black = repr(model.players[BLACK])
    result = model.status
    eco = model.tags.get("ECO")
    board = int(model.tags.get("Board")) if model.tags.get("Board") else None
    white_elo = int(model.tags.get("WhiteElo")) if model.tags.get("WhiteElo") else None
    black_elo = int(model.tags.get("BlackElo")) if model.tags.get("BlackElo") else None
    variant = 1 if issubclass(model.variant, FischerRandomChess) else None
    fen = model.boards[0].asFen() if model.boards[0].asFen() != FEN_START else None
    annotator = model.tags.get("Annotator")
    ply_count = model.ply-model.lowply

    def get_id(table, name):
        if not name:
            return None

        s = select([table.c.id], table.c.name==name.decode("utf_8"))
        result = conn.execute(s)
        id_ = result.scalar()
        if id_ is None:
            result = conn.execute(table.insert().values(name=name.decode("utf_8")))
            id_ = result.inserted_primary_key[0]
        return id_

    conn = engine.connect()

    event_id = get_id(event, game_event)
    site_id = get_id(site, game_site)
    white_id = get_id(player, white)
    black_id = get_id(player, black)
    annotator_id = get_id(player, annotator)

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
        'board': board,
        'fen': fen,
        'variant': variant,
        'annotator_id': annotator_id,
        'movelist': movelist.tostring(),
        'comments': "|".join(comments).decode("utf_8"),
        }

    if hasattr(model, "game_id") and model.game_id is not None:
        result = conn.execute(game.update().where(game.c.id==model.game_id).values(new_values))
    else:
        result = conn.execute(game.insert().values(new_values))
        model.game_id = result.inserted_primary_key


def walk(node, arr, txt):
    while True: 
        if node is None:
            break
        
        # Initial game or variation comment
        if node.prev is None:
            for child in node.children:
                if isinstance(child, basestring):
                    arr.append(COMMENT)
                    txt.append(child)
            node = node.next
            continue

        arr.append(node.board.history[-1][0])

        for nag in node.nags:
            if nag:
                arr.append(NAG-(int(nag[1:])+1))

        for child in node.children:
            if isinstance(child, basestring):
                # comment
                arr.append(COMMENT)
                txt.append(child)
            else:
                # variations
                arr.append(VARI_START)
                walk(child[0], arr, txt)
                arr.append(VARI_END)

        if node.next:
            node = node.next
        else:
            break


def load(file):
    pl1 = player.alias()
    pl2 = player.alias()
    pl3 = player.alias()

    s = select([game.c.id.label("Id"), pl1.c.name.label('White'), pl2.c.name.label('Black'), game.c.result.label('Result'),
                event.c.name.label('Event'), site.c.name.label('Site'), game.c.round.label('Round'), 
                game.c.date_year.label('Year'), game.c.date_month.label('Month'), game.c.date_day.label('Day'),
                game.c.white_elo.label('WhiteElo'), game.c.black_elo.label('BlackElo'), game.c.eco.label('ECO'),
                game.c.fen.label('Board'), game.c.fen.label('FEN'), game.c.variant.label('Variant'), pl3.c.name.label('Annotator')],
                from_obj=[
                    game.outerjoin(pl1, game.c.white_id==pl1.c.id)\
                        .outerjoin(pl2, game.c.black_id==pl2.c.id)\
                        .outerjoin(event, game.c.event_id==event.c.id)\
                        .outerjoin(site, game.c.site_id==site.c.id)\
                        .outerjoin(pl3, game.c.annotator_id==pl3.c.id)])

    conn = engine.connect()
    result = conn.execute(s)

    colnames = result.keys()
    games = result.fetchall()

    return Database(games, colnames, engine)


class Database(PGNFile):
    def __init__ (self, games, colnames, engine):
        PGNFile.__init__(self, games)
        self.colnames = colnames
        self.engine = engine
        self.comments = []

    def get_movetext(self, gameno):
        s = select([game.c.movelist, game.c.comments], game.c.id==self.games[gameno][0])
        conn = self.engine.connect()
        result = conn.execute(s).first()
        self.comments = result[1].split("|")
        arr = array("h")
        arr.fromstring(result[0])
        return arr

    def loadToModel (self, gameno, position=-1, model=None, quick_parse=True):
        self.comment_idx = 0
        model = PGNFile.loadToModel (self, gameno, position=position, model=model, quick_parse=quick_parse)
        model.game_id = self.games[gameno]["Id"]
        return model

    def _getTag (self, gameno, tagkey):
        if tagkey == "Result":
            return reprResult[self.games[gameno][tagkey]]

        if tagkey == "Date":
            y = self.games[gameno]['Year']
            m = self.games[gameno]['Month']
            d = self.games[gameno]['Day']
            tag_date = "%s.%s.%s" % (y if y else "????", m if m else "??", d if d else "??")
            return tag_date

        if tagkey in self.colnames:
            tag = self.games[gameno][tagkey]
            return "%s" % (tag if tag else "")
        else:
            return ""

    def parse_string(self, movetext, model, board, position, variation=False):
        boards = []

        board = board.clone()
        last_board = board
        boards.append(board)

        error = None
        parenthesis = 0
        v_array = array("h")
        prev_elem = -9999
        for i, elem in enumerate(movetext):
            if parenthesis > 0:
                v_array.append(elem)

            if elem == VARI_END:
                parenthesis -= 1
                if parenthesis == 0:
                    v_last_board.children.append(self.parse_string(v_array[:-1], model, board.prev, position, variation=True))
                    v_array = array("h")
                    prev_elem = VARI_END
                    continue

            elif elem == VARI_START:
                parenthesis += 1
                if parenthesis == 1:
                    v_last_board = last_board

            if parenthesis == 0:
                if elem > 0:
                    if not variation:
                        if position != -1 and board.ply >= position:
                            break

                    move = Move(elem)
                    board = boards[-1].move(move)
                    
                    ply = boards[-1].ply
                    if ply % 2 == 0:
                        mvcount = "%d." % (ply/2+1)
                    elif prev_elem < 0:
                        mvcount = "%d..." % (ply/2+1)
                    else:
                        mvcount = ""        
                    board.movecount = mvcount

                    if last_board:
                        board.prev = last_board
                        last_board.next = board

                    boards.append(board)
                    last_board = board

                    if not variation:
                        model.moves.append(move)

                elif elem == COMMENT:
                    comment = self.comments[self.comment_idx]
                    self.comment_idx += 1
                    last_board.children.append(comment)

                elif elem <= NAG:
                    # NAG
                    board.nags.append("$%s" % (-(elem-NAG+1)))

                else:
                    print "Unknown element in movelist array:", elem

            if elem > NAG:
                prev_elem = elem

            if error:
                raise error

        return boards

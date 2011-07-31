# -*- coding: UTF-8 -*-

from array import array

from sqlalchemy import create_engine, select, and_

from pgn import PGNFile
from pychess.Utils.const import reprResult
from pychess.Utils.Board import Board
from pychess.Utils.Move import Move
from pychess.Database.model import engine, metadata, event, site, player, game

__label__ = _("PyChess database")
__endings__ = "pdb",
__append__ = True

COMMENT, VARI_START, VARI_END, NAG = -1, -2, -3, -4

def save (file, model):
    movelist = array("h")
    comments = []
    walk(model.boards[0], movelist, comments)
    if hasattr(model, "game_id") and model.game_id is not None:
        # append
        pass
    else:
        # replace
        pass

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
                game.c.fen.label('FEN'), game.c.variant.label('Variant'), pl3.c.name.label('Annotator')],
                and_(game.c.white_id==pl1.c.id, game.c.black_id==pl2.c.id,
                     game.c.event_id==event.c.id, game.c.site_id==site.c.id,
                     game.c.annotator_id==pl3.c.id))
                 
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
        s = select([game.c.movelist, game.c.comments], and_(game.c.id==self.games[gameno][0]))
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

from __future__ import print_function

import unittest

from pychess.compat import StringIO
from pychess.Utils.const import FEN_START, LOCAL
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmovegen import genAllMoves
from pychess.Savers.database import save, load
from pychess.Savers.pgn import load as pgnload
from pychess.Savers.pgn import walk
from pychess.Database.model import get_engine, metadata


class TestPlayer():
    __type__ = LOCAL

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


pgnfile0 = pgnload(open('gamefiles/annotated.pgn'))

pgnfile1 = pgnload(StringIO(
    """
[Event "win"]
[Result "1-0"]
1. e4 e5 2. Nf3 Nf6 3. Nc3 Nc6

[Event "draw"]
[Result "1/2-1/2"]
1. d4 d5 2. Nf3 Nf6

[Event "win"]
[Result "1-0"]
1. c4 c5 2. Nf3 Nf6

[Event "win"]
[Result "0-1"]
1. c4 c5 2. Nc3 Nf6
"""))

GAME_COUNT = len(pgnfile1.games)
BITBOARD_COUNT = (0, 3, 3, 4, 4)


class DbTestCase(unittest.TestCase):
    def setUp(self):
        self.test_db = None  # "/home/tamas/test.pdb"
        self.engine = get_engine(self.test_db)

    def tearDown(self):
        if self.test_db is None:
            metadata.drop_all(self.engine)
            metadata.create_all(self.engine)

    def load_test_pgn(self):
        for gameno in range(GAME_COUNT):
            game_model = pgnfile1.loadToModel(gameno)
            game_model.players = (TestPlayer("White"), TestPlayer("Black"))
            save(self.test_db, game_model)

        return load(self.test_db)

    def test_database_save_load(self):
        """Testing database save-load"""

        game_model = pgnfile0.loadToModel(0)

        p0, p1 = pgnfile0.get_player_names(0)
        game_model.players = (TestPlayer(p0), TestPlayer(p1))

        in_game = []
        walk(game_model.boards[0].board, in_game, game_model)
        in_game = " ".join(in_game)

        in_bb_list = [board.board.friends for board in game_model.boards]

        save(None, game_model)

        db = load(None)

        result = self.engine.execute(db.select)
        db.games = result.fetchall()
        print("%s selected" % len(db.games))

        game_model = db.loadToModel(0)

        out_game = []
        walk(game_model.boards[0].board, out_game, game_model)
        out_game = " ".join(out_game)

        out_bb_list = [board.board.friends for board in game_model.boards]

        self.assertEqual(in_game, out_game)
        self.assertEqual(in_bb_list, out_bb_list)

    def test_pgn_database_get_records(self):
        """Testing .pgn database get_records"""

        pgnfile1.build_where_tags("win")
        pgnfile1.build_query()
        records = pgnfile1.get_records(0, 100)

        self.assertEqual(len(records), 3)

    def test_pdb_database_get_records(self):
        """Testing .pdb database get_records"""

        db = self.load_test_pgn()

        db.build_where_tags("win")
        db.build_query()
        db.get_records(0, 100)

        print("==========")
        games_count = 0
        for g in db.games:
            print(g["Id"], g["Event"], g["Result"])
            games_count += 1
        print("----------")

        self.assertEqual(games_count, 3)

        db.update_count()
        self.assertEqual(db.count, 3)

    def test_pdb_database_get_bitboards(self):
        """Testing .pdb database get_bitboards"""

        db = self.load_test_pgn()

        board = LBoard()
        board.applyFen(FEN_START)

        def get_bb_candidates(board):
            bb_candidates = {}
            for lmove in genAllMoves(board):
                board.applyMove(lmove)
                if board.opIsChecked():
                    board.popMove()
                    continue
                bb_candidates[board.friends[0] | board.friends[1]] = lmove
                board.popMove()
            return bb_candidates

        bitboards = db.get_bitboards(1, get_bb_candidates(board))
        print("==========")
        for row in bitboards:
            print(row)
        print("----------")
        self.assertEqual(len(bitboards), BITBOARD_COUNT[1])
        self.assertEqual(sum([row[1] for row in bitboards]), GAME_COUNT)


if __name__ == '__main__':
    unittest.main()

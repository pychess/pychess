from __future__ import print_function

import unittest

from pychess.compat import StringIO
from pychess.Utils.const import LOCAL
from pychess.Savers.database import save, load
from pychess.Savers.pgn import load as pgnload
from pychess.Savers.pgn import walk
from pychess.Database import model
from pychess.Database.model import metadata


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
BITBOARD_COUNT = (1, 3, 3, 4)


class DbTestCase(unittest.TestCase):
    def setUp(self):
        model.set_engine("sqlite://")
        metadata.create_all(model.engine)

    def load_test_pgn(self):
        for gameno in range(GAME_COUNT):
            game_model = pgnfile1.loadToModel(gameno)
            game_model.players = (TestPlayer("White"), TestPlayer("Black"))
            save(None, game_model)

        return load(None)

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

        result = model.engine.execute(db.select0)
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
        pgnfile1.get_records(0, 100)

        self.assertEqual(len(pgnfile1.games), 3)

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

        for ply in range(4):
            bitboards = db.get_bitboards(ply)
            self.assertEqual(len(bitboards), BITBOARD_COUNT[ply])
            self.assertEqual(sum([row[1] for row in bitboards]), GAME_COUNT)


if __name__ == '__main__':
    unittest.main()

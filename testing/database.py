from __future__ import print_function
import unittest

from pychess.Utils.const import *
from pychess.Savers.database import save, load
from pychess.Savers.pgn import load as pgnload
from pychess.Savers.pgn import walk
from pychess.Database import model
from pychess.Database.model import set_engine, metadata, collection, event,\
                            site, player, game, annotator, ini_collection

class TestPlayer():
    __type__ = LOCAL
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return self.name

pgnfile = pgnload(open('gamefiles/annotated.pgn'))

class DbTestCase(unittest.TestCase):
    
    def setUp(self):
        model.set_engine("sqlite://")
        metadata.create_all(model.engine)
        self.conn = model.engine.connect()
    
    def test_databas(self):
        """Testing database save-load"""

        model = pgnfile.loadToModel(0)
        
        p0, p1 = pgnfile.get_player_names(0)
        model.players = (TestPlayer(p0), TestPlayer(p1))

        in_game = []
        walk(model.boards[0].board, in_game, model)
        in_game = " ".join(in_game)
        
        save(None, model)

        db = load(None)

        result = self.conn.execute(db.select)
        db.games = result.fetchall()
        print("%s selected" % len(db.games))

        model = db.loadToModel(0)

        out_game = []
        walk(model.boards[0].board, out_game, model)
        out_game = " ".join(out_game)
        
        self.assertEqual(in_game, out_game)
            
if __name__ == '__main__':
    unittest.main()


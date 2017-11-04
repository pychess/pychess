import asyncio
import logging
import unittest

from pychess.Utils.Move import Move
from pychess.Utils.lutils.lmovegen import newMove
from pychess.Utils.GameModel import GameModel
from pychess.Utils.TimeModel import TimeModel
from pychess.Utils.const import WHITE, BLACK, LOCAL, F2, F3, E7, E5, G2, G4, D8, H4
from pychess.Players.Human import Human
from pychess.System import conf, uistuff
from pychess.widgets import gamewidget
from pychess.perspectives import perspective_manager
from pychess.perspectives.games import Games
from pychess.perspectives.database import Database
from pychess.perspectives.welcome import Welcome
from pychess.System.Log import log
log.logger.setLevel(logging.INFO)


class SaveGameTests(unittest.TestCase):

    def test(self):
        """ Play and save Human-Human 1 min game """
        widgets = uistuff.GladeWidgets("PyChess.glade")
        gamewidget.setWidgets(widgets)
        perspective_manager.set_widgets(widgets)

        self.welcome_persp = Welcome()
        perspective_manager.add_perspective(self.welcome_persp)

        self.games_persp = Games()
        perspective_manager.add_perspective(self.games_persp)

        self.database_persp = Database()
        perspective_manager.add_perspective(self.database_persp)
        self.database_persp.create_toolbuttons()

        self.loop = asyncio.get_event_loop()
        self.loop.set_debug(enabled=True)

        def coro():
            gamemodel = GameModel(TimeModel(1, 0))

            player0tup = (LOCAL, Human, (WHITE, "w"), "w")
            player1tup = (LOCAL, Human, (BLACK, "b"), "b")

            def on_game_end(game, state, event):
                event.set()

            event = asyncio.Event()
            gamemodel.connect("game_ended", on_game_end, event)

            def on_players_changed(game):
                # fill fools mate moves to players move queue
                p0 = game.players[0]
                p0.queue.put_nowait(Move(newMove(F2, F3)))
                p0.queue.put_nowait(Move(newMove(G2, G4)))

                p1 = gamemodel.players[1]
                p1.queue.put_nowait(Move(newMove(E7, E5)))
                p1.queue.put_nowait(Move(newMove(D8, H4)))

            gamemodel.connect("players_changed", on_players_changed)

            asyncio.async(self.games_persp.generalStart(gamemodel, player0tup, player1tup))

            # waiting for game end ...
            yield from event.wait()

            fen = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
            self.assertEqual(gamemodel.boards[-1].board.asFen(), fen)

            # Now save our game to pychess.pgn
            def on_game_saved(game, uri):
                self.database_persp.open_chessfile(uri)

                self.database_persp.chessfile.games[0]
                self.assertEqual(self.database_persp.chessfile.count, 1)

            gamemodel.connect("game_saved", on_game_saved)

            conf.set("saveOwnGames", True)
            self.games_persp.saveGamePGN(gamemodel)

        self.loop.run_until_complete(coro())


if __name__ == '__main__':
    unittest.main()

from pychess.Database.gamelist import GameList
from pychess.perspectives import Perspective


class Database(Perspective):
    def __init__(self):
        Perspective.__init__(self, "database", _("Database"))
        game_list = GameList()
        self.widget.add(game_list.vbox)

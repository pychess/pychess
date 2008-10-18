from datetime import date

import gtk

from pychess.Utils.const import *
from pychess.System.prefix import addDataPrefix
from pychess.System.glock import glock_connect

__title__ = _("Game list")
__active__ = True
__icon__ = addDataPrefix("glade/panel_moves.svg")
__desc__ = _("You can load another game from the list.")


class Sidepanel(gtk.TreeView):
    def load (self, gmwidg):
        widgets = gtk.glade.XML(addDataPrefix("sidepanel/book.glade"))
        self.tv = widgets.get_widget("treeview")
        self.sw = widgets.get_widget("scrolledwindow")
        self.sw.unparent()
        
        self.store = gtk.ListStore(int, str, str, str, str, str, str, str, str)
        self.tv.set_model(self.store)
        self.tv.get_selection().set_mode(gtk.SELECTION_BROWSE)
        self.tv.set_headers_visible(True)
        
        cols = ("No", "White", "W Elo", "Black", "B Elo",
                "Result", "Event", "Round", "Date")
        for i, col in enumerate(cols):
            r = gtk.CellRendererText()
            column = gtk.TreeViewColumn(col, r, text=i)
            column.set_resizable(True)
            self.tv.append_column(column)

        self.model = gmwidg.board.view.model
        glock_connect(self.model, "game_loading", self.game_loading)
        self.tv.connect("row-activated", self.row_activated)

        self.tv.set_cursor(0)
        self.tv.columns_autosize()
        self.uri = None
        
        return self.sw

    def game_loading(self, model, uri):
        if self.uri != uri:
            self.uri = uri
            self.store.clear()
            from pychess.Main import chessFiles
            if chessFiles.has_key(self.uri):
                cf = chessFiles[self.uri]
                games = cf.games
                for i, game in enumerate(games):
                    name = cf.get_player_names(i)
                    elo = cf.get_elo(i)
                    result = reprResult[cf.get_result(i)]
                    event = cf.get_event(i)
                    round = cf.get_round(i)
                    y, m, d = cf.get_date(i)
                    edate = str(date(y, m, d))
                    self.store.append([i, name[0], elo[0], name[1], elo[1],
                                       result, event, round, edate])
        self.tv.set_cursor(model.gameno)
    
    def row_activated (self, widget, path, col):
        from pychess.Players.Human import Human
        from pychess.widgets import ionest
        from pychess.Utils.GameModel import GameModel

        gamemodel = GameModel()
        p0 = (LOCAL, Human, (WHITE, ""), _("Human"))
        p1 = (LOCAL, Human, (BLACK, ""), _("Human"))
        gameno = path[0]
        position = -1
        ionest.generalStart(gamemodel, p0, p1, (self.uri, None, gameno, position))
        
        # TODO: find a better solution to preserve the actual row
        #self.tv.set_cursor(self.model.gameno)

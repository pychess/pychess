# -*- coding: UTF-8 -*-

import gtk

from pychess.Database.model import pychess_pdb
from pychess.Savers.database import load
from pychess.Utils.const import *
from pychess.System.prefix import addDataPrefix
from pychess.System.glock import glock_connect
from pychess.Players.Human import Human
from pychess.widgets import ionest
from pychess.Utils.GameModel import GameModel


class GameList(gtk.TreeView):
    def __init__(self):
        gtk.TreeView.__init__(self)
        
        self.store = gtk.ListStore(int, str, str, str, str, str, str, str, str, str, str)
        model = gtk.TreeModelSort(self.store)
        model.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.set_model(model)
        self.get_selection().set_mode(gtk.SELECTION_BROWSE)
        self.set_headers_visible(True)
        self.set_rules_hint(True)
        self.set_search_column(1)
        
        cols = ("No", "White", "W Elo", "Black", "B Elo",
                "Result", "Event", "Site", "Round", "Date", "ECO")
        for i, col in enumerate(cols):
            r = gtk.CellRendererText()
            column = gtk.TreeViewColumn(col, r, text=i)
            column.set_resizable(True)
            column.set_reorderable(True)
            column.set_sort_column_id(i)
            column.connect("clicked", self.column_clicked, i)
            self.append_column(column)

        self.connect("row-activated", self.row_activated)

        self.set_cursor(0)
        self.columns_autosize()
        self.gameno = 0
        self.uri = pychess_pdb
        self.chessfile = None
        
        w = gtk.Window(gtk.WINDOW_TOPLEVEL)
        w.set_title(_("PyChess Game Database"))
        w.set_size_request(1200, 400)
        vbox = gtk.VBox()
        sw = gtk.ScrolledWindow()
        sw.add(self)
        vbox.pack_start(sw)
        w.add(vbox)
        w.show_all()
        
    def column_clicked(self, col, data):
        self.set_search_column(data)
        
    def load_games(self):
        self.store.clear()
        self.chessfile = cf = load(open(self.uri))
        games = cf.games
        for i, game in enumerate(games):
            wname, bname = cf.get_player_names(i)
            welo = cf._getTag(i, "WhiteElo")
            belo = cf._getTag(i, "BlackElo")
            result = cf.get_result(i)
            result = "½-½" if result==DRAW else reprResult[cf.get_result(i)]
            event = cf._getTag(i, 'Event')
            site = cf._getTag(i, 'Site')
            round = cf._getTag(i, "Round")
            date = cf._getTag(i, "Date")
            eco = cf._getTag(i, "ECO")
            self.store.append([i, wname, welo, bname, belo,
                               result, event, site, round, date, eco])
        self.set_cursor(0)
    
    def row_activated (self, widget, path, col):
        gameno = path[0]
        position = -1

        gamemodel = GameModel()
        wp, bp = self.chessfile.get_player_names(gameno)
        p0 = (LOCAL, Human, (WHITE, wp), wp)
        p1 = (LOCAL, Human, (BLACK, bp), bp)
        self.chessfile.loadToModel(gameno, -1, gamemodel, False)

        gamemodel.status = WAITING_TO_START
        ionest.generalStart(gamemodel, p0, p1)

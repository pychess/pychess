from __future__ import print_function
# -*- coding: UTF-8 -*-

from gi.repository import Gtk, GObject

from sqlalchemy import select, func, and_, or_

from pychess.Database.model import engine, game, player, pl1, pl2, pychess_pdb
from pychess.Savers.database import load
from pychess.Utils.const import *
from pychess.System.prefix import addDataPrefix
from pychess.Players.Human import Human
from pychess.widgets import ionest
from pychess.Utils.GameModel import GameModel


class GameList(Gtk.TreeView):

    STEP = 50

    def __init__(self):
        GObject.GObject.__init__(self)
        
        self.offset = 0
        self.orderby = None
        self.where = None
        self.count = 0
        self.conn = engine.connect()
        
        self.liststore = Gtk.ListStore(int, str, str, str, str, str, str, str, str, str, str)
        self.modelsort = Gtk.TreeModelSort(self.liststore)
        
        self.modelsort.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.set_model(self.modelsort)
        self.get_selection().set_mode(Gtk.SelectionMode.BROWSE)
        self.set_headers_visible(True)
        self.set_rules_hint(True)
        self.set_search_column(1)
        
        cols = (_("Id"), _("White"), _("W Elo"), _("Black"), _("B Elo"),
                _("Result"), _("Event"), _("Site"), _("Round"), _("Date"), _("ECO"))
        for i, col in enumerate(cols):
            r = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col, r, text=i)
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

        self.chessfile = load(open(self.uri))
        self.build_query()

        w = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        w.set_title(_("PyChess Game Database"))
        w.set_size_request(1000, 400)

        hbox = Gtk.HBox()

        self.playerlist = Gtk.ListStore(str)

        self.match = set()
        completion = Gtk.EntryCompletion()
        completion.set_model(self.playerlist)
        completion.set_text_column(0)

        for player in self.chessfile.players:
            self.playerlist.append(player)
            
        entry = Gtk.Entry()
        entry.set_completion(completion)
        entry.connect('activate', self.activate_entry)
        
        hbox.pack_start(entry, False, False, 0)

        toolbar = Gtk.Toolbar()
        hbox.pack_start(toolbar, True, True, 0)

        firstButton = Gtk.ToolButton(Gtk.STOCK_MEDIA_PREVIOUS);
        toolbar.insert(firstButton, -1)

        prevButton = Gtk.ToolButton(Gtk.STOCK_MEDIA_REWIND)
        toolbar.insert(prevButton, -1)

        nextButton = Gtk.ToolButton(Gtk.STOCK_MEDIA_FORWARD)
        toolbar.insert(nextButton, -1)

        lastButton = Gtk.ToolButton(Gtk.STOCK_MEDIA_NEXT);
        toolbar.insert(lastButton, -1)

        firstButton.connect("clicked", self.on_first_clicked)
        prevButton.connect("clicked", self.on_prev_clicked)
        nextButton.connect("clicked", self.on_next_clicked)
        lastButton.connect("clicked", self.on_last_clicked)

        vbox = Gtk.VBox()
        vbox.pack_start(hbox, False, False, 0)

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        sw.add(self)
        vbox.pack_start(sw, True, True, 0)
        w.add(vbox)
        w.show_all()

    def build_query(self):
        self.query = self.chessfile.select
        
        if self.where is None:
            self.count = self.chessfile.count
        else:
            s = select([func.count(game.c.id)],\
                from_obj=[
                    game.outerjoin(pl1, game.c.white_id==pl1.c.id)\
                        .outerjoin(pl2, game.c.black_id==pl2.c.id)])
            self.count = self.conn.execute(s.where(self.where)).scalar()
            self.query = self.query.where(self.where)
        print("%s game(s) match to query" % self.count)

        if self.orderby is not None:
            self.query = self.query.order_by(self.orderby)
        
    def activate_entry(self, entry):
        text = entry.get_text()
        self.where = or_(pl1.c.name.startswith(text), pl2.c.name.startswith(text))
        self.offset = 0
        self.build_query()
        self.load_games()

    def on_first_clicked(self, widget):
        self.offset = 0
        self.load_games()

    def on_prev_clicked(self, widget):
        if self.offset - self.STEP >= 0:
            self.offset = self.offset - self.STEP
            self.load_games()

    def on_next_clicked(self, widget):
        if self.offset + self.STEP <= self.count:
            self.offset = self.offset + self.STEP
            self.load_games()

    def on_last_clicked(self, widget):
        self.offset = (self.count // self.STEP) * self.STEP
        self.load_games()
        
    def column_clicked(self, col, data):
        self.set_search_column(data)
        
    def load_games(self):
        self.liststore.clear()

        getTag = self.chessfile._getTag
        getResult = self.chessfile.get_result
        getPlayers = self.chessfile.get_player_names
        add = self.liststore.append

        query = self.query.offset(self.offset).limit(self.STEP)
        
        result = self.conn.execute(query)
        self.chessfile.games = result.fetchall()
        print("%s selected" % len(self.chessfile.games))
        self.id_list = []
        for i in range(len(self.chessfile.games)):
            game_id = self.chessfile.games[i]["Id"]
            self.id_list.append(game_id)
            wname, bname = getPlayers(i)
            welo = getTag(i, "WhiteElo")
            belo = getTag(i, "BlackElo")
            result = getResult(i)
            result = "½-½" if result==DRAW else reprResult[result]
            event = getTag(i, 'Event')
            site = getTag(i, 'Site')
            round_ = getTag(i, "Round")
            date = getTag(i, "Date")
            eco = getTag(i, "ECO")
            add([game_id, wname, welo, bname, belo, result, event, site, round_, date, eco])
        self.set_cursor(0)
    
    def row_activated (self, widget, path, col):
        print(self.modelsort.convert_path_to_child_path(path)[0])
        game_id = self.liststore[self.modelsort.convert_path_to_child_path(path)[0]][0]
        print("game_id=%s" % game_id)
        gameno = self.id_list.index(game_id)
        print("gameno=%s" % gameno)
        position = -1

        gamemodel = GameModel()
        wp, bp = self.chessfile.get_player_names(gameno)
        p0 = (LOCAL, Human, (WHITE, wp), wp)
        p1 = (LOCAL, Human, (BLACK, bp), bp)
        self.chessfile.loadToModel(gameno, -1, gamemodel)

        gamemodel.status = WAITING_TO_START
        ionest.generalStart(gamemodel, p0, p1)

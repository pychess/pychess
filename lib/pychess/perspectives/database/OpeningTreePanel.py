# -*- coding: UTF-8 -*-
from __future__ import print_function

from gi.repository import Gtk, GObject

from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import toSAN, parseAN
from pychess.Utils.const import FEN_START
from pychess.perspectives import perspective_manager


class OpeningTreePanel(Gtk.TreeView):
    def __init__(self, gamelist):
        GObject.GObject.__init__(self)
        self.gamelist = gamelist

        self.filtered = False

        self.persp = perspective_manager.get_perspective("database")
        self.persp.connect("chessfile_opened", self.on_chessfile_opened)
        self.persp.connect("chessfile_switched", self.on_chessfile_switched)
        self.persp.connect("chessfile_imported", self.on_chessfile_imported)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.liststore = Gtk.ListStore(int, str, int, int)
        self.modelsort = Gtk.TreeModelSort(self.liststore)

        self.modelsort.set_sort_column_id(2, Gtk.SortType.DESCENDING)
        self.set_model(self.modelsort)

        self.set_headers_visible(True)

        column = Gtk.TreeViewColumn(_("Move"), Gtk.CellRendererText(), text=1)
        column.set_sort_column_id(1)
        column.connect("clicked", self.column_clicked, 1)
        self.append_column(column)

        column = Gtk.TreeViewColumn(_("Games"), Gtk.CellRendererText(), text=2)
        column.set_sort_column_id(2)
        column.connect("clicked", self.column_clicked, 2)
        self.append_column(column)

        column = Gtk.TreeViewColumn(_("Winning %"), Gtk.CellRendererProgress(), value=3)
        column.set_min_width(80)
        column.set_sort_column_id(3)
        column.connect("clicked", self.column_clicked, 3)
        self.append_column(column)

        self.conid = self.connect_after("row-activated", self.row_activated)

        self.board = LBoard()
        self.board.applyFen(FEN_START)

        self.columns_autosize()

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        sw.add(self)

        self.box.pack_start(sw, True, True, 0)

        #  buttons
        toolbar = Gtk.Toolbar()

        firstButton = Gtk.ToolButton(Gtk.STOCK_MEDIA_PREVIOUS)
        toolbar.insert(firstButton, -1)

        prevButton = Gtk.ToolButton(Gtk.STOCK_MEDIA_REWIND)
        toolbar.insert(prevButton, -1)

        filterButton = Gtk.ToggleToolButton(Gtk.STOCK_FIND)
        toolbar.insert(filterButton, -1)

        firstButton.connect("clicked", self.on_first_clicked)
        prevButton.connect("clicked", self.on_prev_clicked)
        filterButton.connect("clicked", self.on_filter_clicked)

        tool_box = Gtk.Box()
        tool_box.pack_start(toolbar, False, False, 0)
        self.box.pack_start(tool_box, False, False, 0)

        self.box.show_all()

    def on_chessfile_opened(self, persp, chessfile):
        self.update_tree(load_games=False)

    def on_chessfile_switched(self, switcher, chessfile):
        self.update_tree()

    def on_chessfile_imported(self, persp, chessfile):
        self.update_tree()

    def on_first_clicked(self, widget):
        while self.board.hist_move:
            self.board.popMove()
        self.update_tree()

    def on_prev_clicked(self, widget):
        if self.board.hist_move:
            self.board.popMove()
        self.update_tree()

    def on_filter_clicked(self, button):
        self.filtered = button.get_active()

    def column_clicked(self, col, data):
        self.set_search_column(data)

    def row_activated(self, widget, path, col):
        lmove = self.liststore[self.modelsort.convert_path_to_child_path(path)[0]][0]
        self.board.applyMove(lmove)
        self.update_tree()

    def update_tree(self, load_games=True):
        self.gamelist.ply = self.board.plyCount
        self.gamelist.chessfile.set_fen_filter(self.board.asFen())
        if load_games and self.filtered:
            self.gamelist.load_games()

        result = self.gamelist.chessfile.get_book_moves(self.board.asFen())
        self.clear_tree()
        for move, count, white_won, blackwon, draw in result:
            lmove = parseAN(self.board, move)
            perf = 0 if not count else round((white_won * 100. + draw * 50.) / count)
            self.liststore.append([lmove, toSAN(self.board, lmove), count, perf])

    def clear_tree(self):
        selection = self.get_selection()
        if self.conid is not None and selection.handler_is_connected(self.conid):
            with GObject.signal_handler_block(selection, self.conid):
                self.liststore.clear()
        else:
            self.liststore.clear()

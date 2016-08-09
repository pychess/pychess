# -*- coding: UTF-8 -*-
from __future__ import print_function

from gi.repository import Gtk, GObject

from pychess.Utils.lutils.lmovegen import genAllMoves
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import toSAN
from pychess.Utils.const import FEN_START, WHITE
from pychess.perspectives import perspective_manager


class OpeningTreePanel(Gtk.TreeView):
    def __init__(self, gamelist):
        GObject.GObject.__init__(self)
        self.gamelist = gamelist

        persp = perspective_manager.get_perspective("database")
        persp.connect("chessfile_opened", self.on_chessfile_opened)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.liststore = Gtk.ListStore(int, str, int, int, int)
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

        column = Gtk.TreeViewColumn(_("Result"), Gtk.CellRendererProgress(), value=3)
        column.set_min_width(80)
        column.set_sort_column_id(3)
        column.connect("clicked", self.column_clicked, 3)
        self.append_column(column)

        column = Gtk.TreeViewColumn(_("Elo Avg"), Gtk.CellRendererText(), text=4)
        column.set_sort_column_id(4)
        column.connect("clicked", self.column_clicked, 4)
        self.append_column(column)

        self.conid = self.connect_after("row-activated", self.row_activated)

        self.board = LBoard()
        self.board.applyFen(FEN_START)
        self.update_tree(self.board)

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

        firstButton.connect("clicked", self.on_first_clicked)
        prevButton.connect("clicked", self.on_prev_clicked)

        tool_box = Gtk.Box()
        tool_box.pack_start(toolbar, False, False, 0)
        self.box.pack_start(tool_box, False, False, 0)

        self.box.show_all()

    def on_chessfile_opened(self, persp, chessfile):
        self.on_first_clicked(None)

    def on_first_clicked(self, widget):
        while self.board.hist_move:
            self.board.popMove()
        bb = self.board.friends[0] | self.board.friends[1]

        self.gamelist.ply = self.board.plyCount
        self.gamelist.chessfile.build_where_bitboards(self.board.plyCount, bb)
        self.gamelist.offset = 0
        self.gamelist.chessfile.build_query()
        self.gamelist.load_games()

        self.update_tree(self.board)

    def on_prev_clicked(self, widget):
        # TODO: disable buttons instead
        if not self.board.hist_move:
            return
        self.board.popMove()
        bb = self.board.friends[0] | self.board.friends[1]

        self.gamelist.ply = self.board.plyCount
        self.gamelist.chessfile.build_where_bitboards(self.board.plyCount, bb)
        self.gamelist.offset = 0
        self.gamelist.chessfile.build_query()
        self.gamelist.load_games()

        self.update_tree(self.board)

    def column_clicked(self, col, data):
        self.set_search_column(data)

    def row_activated(self, widget, path, col):
        lmove = self.liststore[self.modelsort.convert_path_to_child_path(path)[0]][0]
        self.board.applyMove(lmove)
        bb = self.board.friends[0] | self.board.friends[1]

        self.gamelist.ply = self.board.plyCount
        self.gamelist.chessfile.build_where_bitboards(self.board.plyCount, bb)
        self.gamelist.offset = 0
        self.gamelist.chessfile.build_query()
        self.gamelist.load_games()
        self.update_tree(self.board)
        self.gamelist.chessfile.update_count()

    def update_tree(self, board):
        bb_candidates = {}
        for lmove in genAllMoves(board):
            board.applyMove(lmove)
            if board.opIsChecked():
                board.popMove()
                continue
            bb_candidates[board.friends[0] | board.friends[1]] = lmove
            board.popMove()

        result = []
        bb_list = self.gamelist.chessfile.get_bitboards(board.plyCount + 1, bb_candidates)

        for bb, count, white_won, blackwon, draw, white_elo_avg, black_elo_avg in bb_list:
            result.append((bb_candidates[bb], count, white_won, blackwon, draw, white_elo_avg, black_elo_avg))

        selection = self.get_selection()
        if self.conid is not None and selection.handler_is_connected(self.conid):
            with GObject.signal_handler_block(selection, self.conid):
                self.liststore.clear()
        else:
            self.liststore.clear()
        for lmove, count, white_won, blackwon, draw, white_elo_avg, black_elo_avg in result:
            perf = round((white_won * 100. + draw * 50.) / count)
            elo_avg = white_elo_avg if board.color == WHITE else black_elo_avg
            self.liststore.append([lmove, toSAN(self.board, lmove), count, perf, elo_avg])

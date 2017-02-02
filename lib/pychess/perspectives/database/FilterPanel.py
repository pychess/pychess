# -*- coding: UTF-8 -*-
from __future__ import print_function

from gi.repository import GLib, Gtk, GObject

from pychess.Utils.const import chr2Sign, WHITE, BLACK
from pychess.Utils.Piece import Piece
from pychess.Utils.SetupModel import SetupModel, SetupPlayer
from pychess.System import uistuff
from pychess.widgets.BoardControl import BoardControl
from pychess.widgets.PieceWidget import PieceWidget

TAG_FILTER, MATERIAL_FILTER, PATTERN_FILTER = 0, 1, 2


def formatted(q):
    """ Simplified textual representation of query """
    q = "%s" % q
    return q[1:-1].replace("'", "")


class FilterPanel(Gtk.TreeView):
    def __init__(self, gamelist):
        GObject.GObject.__init__(self)
        self.gamelist = gamelist

        # Add piece widgets to dialog *_dock containers on material tab
        self.widgets = uistuff.GladeWidgets("PyChess.glade")
        self.dialog = self.widgets["filter_dialog"]

        for piece in "qrbnp":
            dock = "w%s_dock" % piece
            self.widgets[dock].add(PieceWidget(Piece(WHITE, chr2Sign[piece])))
            self.widgets[dock].get_child().show()

            dock = "b%s_dock" % piece
            self.widgets[dock].add(PieceWidget(Piece(BLACK, chr2Sign[piece])))
            self.widgets[dock].get_child().show()

            dock = "moved_%s_dock" % piece
            self.widgets[dock].add(PieceWidget(Piece(BLACK, chr2Sign[piece])))
            self.widgets[dock].get_child().show()

            dock = "captured_%s_dock" % piece
            self.widgets[dock].add(PieceWidget(Piece(BLACK, chr2Sign[piece])))
            self.widgets[dock].get_child().show()

        piece = "k"
        dock = "moved_%s_dock" % piece
        self.widgets[dock].add(PieceWidget(Piece(BLACK, chr2Sign[piece])))
        self.widgets[dock].get_child().show()

        # We will store our filtering queries in a ListStore
        # column 0: query as text
        # column 1: query dict
        # column 2: query type (TAG_FILTER or MATERIAL_FILTER or PATTERN_FILTER)
        self.liststore = Gtk.ListStore(str, object, int)

        self.set_model(self.liststore)

        self.set_headers_visible(True)

        column = Gtk.TreeViewColumn("filter", Gtk.CellRendererText(), text=0)
        column.set_min_width(80)
        self.append_column(column)

        self.columns_autosize()

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        sw.add(self)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.pack_start(sw, True, True, 0)

        # Add buttons
        toolbar = Gtk.Toolbar()

        editButton = Gtk.ToolButton(Gtk.STOCK_EDIT)
        editButton.set_tooltip_text(_("Edit selected filter"))
        editButton.connect("clicked", self.on_edit_clicked)
        toolbar.insert(editButton, -1)

        delButton = Gtk.ToolButton(Gtk.STOCK_REMOVE)
        delButton.set_tooltip_text(_("Delete selected filter"))
        delButton.connect("clicked", self.on_del_clicked)
        toolbar.insert(delButton, -1)

        addButton = Gtk.ToolButton(Gtk.STOCK_ADD)
        addButton.set_tooltip_text(_("Create new filter"))
        addButton.connect("clicked", self.on_add_clicked)
        toolbar.insert(addButton, -1)

        tool_box = Gtk.Box()
        tool_box.pack_start(toolbar, False, False, 0)
        self.box.pack_start(tool_box, False, False, 0)

        self.box.show_all()

    def on_del_clicked(self, button):
        selection = self.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is None:
            return

        self.liststore.remove(treeiter)

        self.update_filters()

    def on_add_clicked(self, button):
        self.widgets["tag_filter"].set_sensitive(True)
        self.widgets["material_filter"].set_sensitive(True)
        self.widgets["pattern_filter"].set_sensitive(True)

        self.widgets["filter_notebook"].set_current_page(TAG_FILTER)

        self.ini_widgets_from_query({})

        response = self.dialog.run()

        if response == Gtk.ResponseType.OK:
            tag_query, material_query, pattern_query = self.get_queries_from_widgets()

            if tag_query:
                self.liststore.append([formatted(tag_query), tag_query, TAG_FILTER])

            if material_query:
                self.liststore.append([formatted(material_query), material_query, MATERIAL_FILTER])

            if pattern_query:
                self.liststore.append([formatted(pattern_query), pattern_query, PATTERN_FILTER])

            self.update_filters()

        if hasattr(self, "board_control"):
            self.board_control.emit("action", "CLOSE", None)

        self.dialog.hide()

    def on_edit_clicked(self, button):
        selection = self.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is None:
            return

        text, query, query_type = self.liststore[treeiter]

        self.ini_widgets_from_query(query)

        if query_type == TAG_FILTER:
            self.widgets["tag_filter"].set_sensitive(True)
            self.widgets["material_filter"].set_sensitive(False)
            self.widgets["pattern_filter"].set_sensitive(False)
            self.widgets["filter_notebook"].set_current_page(TAG_FILTER)

        elif query_type == MATERIAL_FILTER:
            self.widgets["material_filter"].set_sensitive(True)
            self.widgets["tag_filter"].set_sensitive(False)
            self.widgets["pattern_filter"].set_sensitive(False)
            self.widgets["filter_notebook"].set_current_page(MATERIAL_FILTER)

        elif query_type == PATTERN_FILTER:
            self.widgets["pattern_filter"].set_sensitive(True)
            self.widgets["tag_filter"].set_sensitive(False)
            self.widgets["material_filter"].set_sensitive(False)
            self.widgets["filter_notebook"].set_current_page(PATTERN_FILTER)

        response = self.dialog.run()

        if response == Gtk.ResponseType.OK:
            tag_query, material_query, pattern_query = self.get_queries_from_widgets()

            if tag_query and query_type == TAG_FILTER:
                self.liststore[treeiter] = [formatted(tag_query), tag_query, TAG_FILTER]

            if material_query and query_type == MATERIAL_FILTER:
                self.liststore[treeiter] = [formatted(material_query), material_query, MATERIAL_FILTER]

            if pattern_query and query_type == PATTERN_FILTER:
                self.liststore[treeiter] = [formatted(pattern_query), pattern_query, PATTERN_FILTER]

            self.update_filters()

        if hasattr(self, "board_control"):
            self.board_control.emit("action", "CLOSE", None)

        self.dialog.hide()

    def update_filters(self):
        tag_query = {}
        scout_query = {}

        for item in self.liststore:
            if item[2] == TAG_FILTER:
                tag_query.update(item[1])
            else:
                scout_query.update(item[1])

        need_update = False
        if tag_query != self.gamelist.chessfile.tag_query:
            self.gamelist.chessfile.set_tag_filter(tag_query)
            need_update = True

        if scout_query != self.gamelist.chessfile.scout_query:
            self.gamelist.chessfile.set_scout_filter(scout_query)
            need_update = True

        if need_update:
            self.gamelist.load_games()

    def ini_widgets_from_query(self, query):
        """ Set filter dialog widget values based on query dict key-value pairs """

        for rule in ("white", "black", "event", "site", "eco_from", "eco_to", "annotator"):
            if rule in query:
                self.widgets[rule].set_text(query[rule])
            else:
                self.widgets[rule].set_text("")

        for rule in ("elo_from", "elo_to", "year_from", "year_to"):
            if rule in query:
                self.widgets[rule].set_value(query[rule])
            else:
                self.widgets[rule].set_value(0)

        if "ignore_tag_colors" in query:
            self.widgets["ignore_tag_colors"].set_active(True)
        else:
            self.widgets["ignore_tag_colors"].set_active(False)

        if "result" in query:
            if query["result"] == "1-0":
                self.widgets["result_1_0"].set_active(True)
            elif query["result"] == "0-1":
                self.widgets["result_0_1"].set_active(True)
            elif query["result"] == "1/2-1/2":
                self.widgets["result_1_2"].set_active(True)
            elif query["result"] == "*":
                self.widgets["result_0_0"].set_active(True)
        else:
            self.widgets["result_1_0"].set_active(False)
            self.widgets["result_0_1"].set_active(False)
            self.widgets["result_1_2"].set_active(False)
            self.widgets["result_0_0"].set_active(False)

        q = None
        white0 = ""
        black0 = ""
        if "material" in query:
            q = query["material"]
        if "imbalance" in query:
            q = query["imbalance"]
            self.widgets["imbalance"].set_active(True)
        else:
            self.widgets["imbalance"].set_active(False)

        self.widgets["ignore_material_colors"].set_active(False)
        if type(q) is list and len(q) == 2:
            if "material" in query:
                _, white0, black0 = q[0].split("K")
                _, white1, black1 = q[1].split("K")
            else:
                white0, black0 = q[0].split("v")
                white1, black1 = q[1].split("v")

            if white0 == black1 and black0 == white1:
                self.widgets["ignore_material_colors"].set_active(True)
        elif q is not None:
            if "material" in query:
                _, white0, black0 = q.split("K")
            else:
                white0, black0 = q.split("v")

        for piece in "QRBNP":
            w = white0.count(piece)
            self.widgets["w%s" % piece.lower()].set_value(w if w > 0 else 0)

            b = black0.count(piece)
            self.widgets["b%s" % piece.lower()].set_value(b if b > 0 else 0)

        if "white-move" in query:
            self.widgets["white_move"].set_text(query["white-move"])
        else:
            self.widgets["white_move"].set_text("")

        if "black-move" in query:
            self.widgets["black_move"].set_text(query["black-move"])
        else:
            self.widgets["black_move"].set_text("")

        moved = "moved" in query
        for piece in "pnbrqk":
            active = moved and piece.upper() in query["moved"]
            self.widgets["moved_%s" % piece].set_active(active)

        captured = "captured" in query
        for piece in "pnbrq0":
            active = captured and piece.upper() in query["captured"]
            self.widgets["captured_%s" % piece].set_active(active)

        if "stm" in query:
            self.widgets["stm"].set_active(True)
            if query["stm"] == "white":
                self.widgets["stm_white"].set_active(True)
            else:
                self.widgets["stm_black"].set_active(True)
        else:
            self.widgets["stm"].set_active(False)

        if "sub-fen" in query:
            sub_fen = query["sub-fen"]
            fen_str = "%s/prnsqkPRNSQK w" % sub_fen
        else:
            sub_fen = ""
            fen_str = "8/8/8/8/8/8/8/8/prnsqkPRNSQK w"
        self.widgets["sub_fen"].set_text(sub_fen)

        # Add a BoardControl widget to dock and initialize it with a new SetupModel
        self.setupmodel = SetupModel()
        self.board_control = BoardControl(self.setupmodel,
                                          {},
                                          setup_position=True,
                                          setup_sub_fen=True)
        self.setupmodel.curplayer = SetupPlayer(self.board_control)
        self.setupmodel.connect("game_changed", self.game_changed)

        child = self.widgets["setup_pattern_dock"].get_child()
        if child is not None:
            self.widgets["setup_pattern_dock"].remove(child)
        self.widgets["setup_pattern_dock"].add(self.board_control)
        self.board_control.show_all()

        self.setupmodel.boards = [self.setupmodel.variant(setup=fen_str)]
        self.setupmodel.variations = [self.setupmodel.boards]

        self.setupmodel.start()

    def get_queries_from_widgets(self):
        """ Build tag and scout query dict from filter dialog widget names and values """

        tag_query = {}
        material_query = {}
        pattern_query = {}

        for rule in ("white", "black", "event", "site", "eco_from", "eco_to", "annotator"):
            if self.widgets[rule].get_text():
                tag_query[rule] = self.widgets[rule].get_text()

        for rule in ("elo_from", "elo_to", "year_from", "year_to"):
            if self.widgets[rule].get_value_as_int():
                tag_query[rule] = self.widgets[rule].get_value_as_int()

        if self.widgets["ignore_tag_colors"].get_active():
            tag_query["ignore_tag_colors"] = True

        if self.widgets["result_1_0"].get_active():
            tag_query["result"] = "1-0"
        if self.widgets["result_0_1"].get_active():
            tag_query["result"] = "0-1"
        if self.widgets["result_1_2"].get_active():
            tag_query["result"] = "1/2-1/2"
        if self.widgets["result_0_0"].get_active():
            tag_query["result"] = "*"

        w_material = []
        for piece in "qrbnp":
            w_material.append(piece.upper() * self.widgets["w%s" % piece].get_value_as_int())

        b_material = []
        for piece in "qrbnp":
            b_material.append(piece.upper() * self.widgets["b%s" % piece].get_value_as_int())

        w_material = "".join(w_material)
        b_material = "".join(b_material)

        if w_material or b_material:
            if self.widgets["imbalance"].get_active():
                material_query["imbalance"] = "%sv%s" % (w_material, b_material)

                if self.widgets["ignore_material_colors"].get_active():
                    material_query["imbalance"] = ["%sv%s" % (w_material, b_material),
                                                   "%sv%s" % (b_material, w_material)]
            else:
                material_query["material"] = "K%sK%s" % (w_material, b_material)

                if self.widgets["ignore_material_colors"].get_active():
                    material_query["material"] = ["K%sK%s" % (w_material, b_material),
                                                  "K%sK%s" % (b_material, w_material)]

        if self.widgets["white_move"].get_text():
            material_query["white-move"] = self.widgets["white_move"].get_text()

        if self.widgets["black_move"].get_text():
            material_query["black-move"] = self.widgets["black_move"].get_text()

        moved = ""
        for piece in "pnbrqk":
            if self.widgets["moved_%s" % piece].get_active():
                moved += piece.upper()
        if moved:
            material_query["moved"] = "%s" % moved

        captured = ""
        for piece in "pnbrq0":
            if self.widgets["captured_%s" % piece].get_active():
                captured += piece.upper()
        if captured:
            material_query["captured"] = "%s" % captured

        if self.widgets["stm"].get_active():
            if self.widgets["stm_white"].get_active():
                material_query["stm"] = "white"
            else:
                material_query["stm"] = "black"

        if self.widgets["sub_fen"].get_text():
            pattern_query["sub-fen"] = self.widgets["sub_fen"].get_text()

        return (tag_query, material_query, pattern_query)

    def fen_changed(self):
        self.widgets["sub_fen"].set_text(self.get_fen())

    def game_changed(self, model, ply):
        GLib.idle_add(self.fen_changed)

    def get_fen(self):
        return self.setupmodel.boards[-1].as_fen()

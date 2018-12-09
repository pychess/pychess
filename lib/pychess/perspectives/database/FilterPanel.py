# -*- coding: UTF-8 -*-
import ast

from gi.repository import GLib, Gdk, Gtk, GObject

from pychess.Utils.const import chr2Sign, WHITE, BLACK, NORMALCHESS
from pychess.Utils.Piece import Piece
from pychess.Utils.SetupModel import SetupModel, SetupPlayer
from pychess.System import uistuff
from pychess.System.prefix import addDataPrefix
from pychess.widgets.BoardControl import BoardControl
from pychess.widgets.gameinfoDialog import on_pick_date
from pychess.widgets.PieceWidget import PieceWidget
from pychess.widgets import mainwindow
from pychess.Variants import name2variant

TAG_FILTER, MATERIAL_FILTER, PATTERN_FILTER, NONE, RULE, SEQUENCE, STREAK = range(7)


def formatted(q):
    """ Simplified textual representation of query """
    q = "%s" % q
    return q[1:-1].replace("'", "")


__title__ = _("Filters")

__icon__ = addDataPrefix("glade/panel_filter.svg")

__desc__ = _("Filters panel can filter game list by various conditions")


class FilterPanel(Gtk.TreeView):
    def __init__(self, persp):
        GObject.GObject.__init__(self)
        self.persp = persp
        self.filtered = False
        self.widgets = uistuff.GladeWidgets("PyChess.glade")

        # Build variant combo model
        variant_store = Gtk.ListStore(str, int)

        for name, variant in sorted(name2variant.items()):
            variant_store.append((name, variant.variant))

        self.widgets["variant"].set_model(variant_store)
        renderer_text = Gtk.CellRendererText()
        self.widgets["variant"].pack_start(renderer_text, True)
        self.widgets["variant"].add_attribute(renderer_text, "text", 0)

        # Connect date_from and date_to to corresponding calendars
        self.widgets["date_from_button"].connect("clicked", on_pick_date, self.widgets["date_from"])
        self.widgets["date_to_button"].connect("clicked", on_pick_date, self.widgets["date_to"])

        # Add piece widgets to dialog *_dock containers on material tab
        self.dialog = self.widgets["filter_dialog"]
        self.dialog.set_transient_for(mainwindow())

        def hide(widget, event):
            widget.hide()
            return True
        self.dialog.connect("delete-event", hide)

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

        self.widgets["copy_sub_fen"].connect("clicked", self.on_copy_sub_fen)
        self.widgets["paste_sub_fen"].connect("clicked", self.on_paste_sub_fen)

        # We will store our filtering queries in a ListStore
        # column 0: query as text
        # column 1: query dict
        # column 2: filter type (NONE, TAG_FILTER or MATERIAL_FILTER or PATTERN_FILTER)
        # column 3: row type (RULE, SEQUENCE, STREAK)
        self.treestore = Gtk.TreeStore(str, object, int, int)

        self.set_model(self.treestore)

        self.set_headers_visible(True)
        self.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)

        column = Gtk.TreeViewColumn(_("Filter"), Gtk.CellRendererText(), text=0)
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

        editButton = Gtk.ToolButton(stock_id=Gtk.STOCK_EDIT)
        editButton.set_tooltip_text(_("Edit selected filter"))
        editButton.connect("clicked", self.on_edit_clicked)
        toolbar.insert(editButton, -1)

        delButton = Gtk.ToolButton(stock_id=Gtk.STOCK_REMOVE)
        delButton.set_tooltip_text(_("Remove selected filter"))
        delButton.connect("clicked", self.on_del_clicked)
        toolbar.insert(delButton, -1)

        addButton = Gtk.ToolButton(stock_id=Gtk.STOCK_ADD)
        addButton.set_tooltip_text(_("Add new filter"))
        addButton.connect("clicked", self.on_add_clicked)
        toolbar.insert(addButton, -1)

        addSeqButton = Gtk.ToolButton()
        addSeqButton.set_label(_("Seq"))
        addSeqButton.set_is_important(True)
        addSeqButton.set_tooltip_text(_("Create new squence where listed conditions may be satisfied at different times in a game"))
        addSeqButton.connect("clicked", self.on_add_sequence_clicked)
        toolbar.insert(addSeqButton, -1)

        addStreakButton = Gtk.ToolButton()
        addStreakButton.set_label(_("Str"))
        addStreakButton.set_is_important(True)
        addStreakButton.set_tooltip_text(_("Create new streak sequence where listed conditions have to be satisfied in consecutive (half)moves"))
        addStreakButton.connect("clicked", self.on_add_streak_clicked)
        toolbar.insert(addStreakButton, -1)

        self.filterButton = Gtk.ToggleToolButton(Gtk.STOCK_FIND)
        self.filterButton.set_tooltip_text(_("Filter game list by various conditions"))
        self.filterButton.connect("clicked", self.on_filter_clicked)
        toolbar.insert(self.filterButton, -1)

        tool_box = Gtk.Box()
        tool_box.pack_start(toolbar, False, False, 0)
        self.box.pack_start(tool_box, False, False, 0)

        self.box.show_all()

    def on_filter_clicked(self, button):
        self.filtered = button.get_active()
        if not self.filtered:
            self.persp.preview_panel.filterButton.set_sensitive(True)
            self.persp.opening_tree_panel.filterButton.set_sensitive(True)
            self.clear_filters()
        else:
            self.persp.preview_panel.filterButton.set_sensitive(False)
            self.persp.opening_tree_panel.filterButton.set_sensitive(False)
            self.update_filters()

    def on_del_clicked(self, button):
        selection = self.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is None:
            return

        self.treestore.remove(treeiter)

        self.update_filters()

    def on_add_sequence_clicked(self, button):
        selection = self.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is None:
            it = self.treestore.append(None, [_("Sequence"), {}, NONE, SEQUENCE])
            self.get_selection().select_iter(it)
        else:
            text, query, query_type, row_type = self.treestore[treeiter]
            if row_type == RULE:
                it = self.treestore.append(None, [_("Sequence"), {}, NONE, SEQUENCE])
                self.get_selection().select_iter(it)

    def on_add_streak_clicked(self, button):
        selection = self.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is None:
            it = self.treestore.append(None, [_("Streak"), {}, NONE, STREAK])
            self.get_selection().select_iter(it)
        else:
            text, query, query_type, row_type = self.treestore[treeiter]
            if row_type == RULE:
                it = self.treestore.append(None, [_("Streak"), {}, NONE, STREAK])
                self.get_selection().select_iter(it)
            elif row_type == SEQUENCE:
                it = self.treestore.append(treeiter, [_("Streak"), {}, NONE, STREAK])
                self.get_selection().select_iter(it)
                self.expand_all()

    def on_add_clicked(self, button):
        self.widgets["tag_filter"].set_sensitive(True)
        self.widgets["material_filter"].set_sensitive(True)
        self.widgets["pattern_filter"].set_sensitive(True)

        self.widgets["filter_notebook"].set_current_page(TAG_FILTER)

        self.ini_widgets_from_query({})

        selection = self.get_selection()
        model, treeiter = selection.get_selected()

        if treeiter is not None:
            text, query, query_type, row_type = self.treestore[treeiter]
            if row_type == RULE:
                treeiter = None

        def on_response(dialog, response):
            if response == Gtk.ResponseType.OK:
                tag_query, material_query, pattern_query = self.get_queries_from_widgets()

                if tag_query:
                    it = self.treestore.append(treeiter, [formatted(tag_query), tag_query, TAG_FILTER, RULE])
                    self.get_selection().select_iter(it)

                if material_query:
                    it = self.treestore.append(treeiter, [formatted(material_query), material_query, MATERIAL_FILTER, RULE])
                    self.get_selection().select_iter(it)

                if pattern_query:
                    it = self.treestore.append(treeiter, [formatted(pattern_query), pattern_query, PATTERN_FILTER, RULE])
                    self.get_selection().select_iter(it)

                self.expand_all()

                self.update_filters()

                if (not self.filtered) and len(self.treestore) == 1:
                    self.filterButton.set_active(True)

            if hasattr(self, "board_control"):
                self.board_control.emit("action", "CLOSE", None, None)

            self.dialog.hide()
            self.dialog.disconnect(handler_id)

        handler_id = self.dialog.connect("response", on_response)
        self.dialog.show()

    def on_edit_clicked(self, button):
        selection = self.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is None:
            return

        text, query, query_type, row_type = self.treestore[treeiter]
        if row_type != RULE:
            return

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

        def on_response(dialog, response):
            if response == Gtk.ResponseType.OK:
                tag_query, material_query, pattern_query = self.get_queries_from_widgets()

                if tag_query and query_type == TAG_FILTER:
                    self.treestore[treeiter] = [formatted(tag_query), tag_query, TAG_FILTER, RULE]

                if material_query and query_type == MATERIAL_FILTER:
                    self.treestore[treeiter] = [formatted(material_query), material_query, MATERIAL_FILTER, RULE]

                if pattern_query and query_type == PATTERN_FILTER:
                    self.treestore[treeiter] = [formatted(pattern_query), pattern_query, PATTERN_FILTER, RULE]

                self.update_filters()

            if hasattr(self, "board_control"):
                self.board_control.emit("action", "CLOSE", None, None)

            self.dialog.hide()
            self.dialog.disconnect(handler_id)

        handler_id = self.dialog.connect("response", on_response)
        self.dialog.show()

    def add_sub_fen(self, sub_fen):
        selection = self.get_selection()
        model, treeiter = selection.get_selected()

        if treeiter is not None:
            text, query, query_type, row_type = self.treestore[treeiter]
            if row_type == RULE:
                treeiter = None

        query = {"sub-fen": sub_fen}
        self.treestore.append(treeiter, [formatted(query), query, PATTERN_FILTER, RULE])
        self.expand_all()
        if self.filtered:
            self.update_filters()

    def clear_filters(self):
        self.persp.chessfile.set_tag_filter(None)
        self.persp.chessfile.set_scout_filter(None)
        self.persp.gamelist.load_games()

    def update_filters(self):
        tag_query = {}
        scout_query = {}

        # level 0
        for row in self.treestore:
            text, query, filter_type, row_type = row

            if row_type == RULE:
                if filter_type == TAG_FILTER:
                    tag_query.update(query)
                else:
                    scout_query.update(query)

            elif row_type == SEQUENCE:
                scout_query["sequence"] = []

                # level 1
                for sub_row in row.iterchildren():
                    stext, squery, sfilter_type, srow_type = sub_row

                    if srow_type == RULE:
                        scout_query["sequence"].append(squery)

                    elif srow_type == STREAK:
                        sub_streak = {"streak": []}

                        # level 2
                        for sub_sub_row in sub_row.iterchildren():
                            sstext, ssquery, ssfilter_type, ssrow_type = sub_sub_row
                            if ssrow_type == RULE:
                                sub_streak["streak"].append(ssquery)

                        scout_query["sequence"].append(sub_streak)

            elif row_type == STREAK:
                scout_query["streak"] = []

                # level 1
                for sub_row in row.iterchildren():
                    stext, squery, sfilter_type, srow_type = sub_row

                    if srow_type == RULE:
                        scout_query["streak"].append(squery)

        need_update = False
        if tag_query != self.persp.chessfile.tag_query:
            if self.filtered:
                self.persp.chessfile.set_tag_filter(tag_query)
            need_update = True

        if scout_query != self.persp.chessfile.scout_query:
            if self.filtered:
                self.persp.chessfile.set_scout_filter(scout_query)
            need_update = True

        textbuffer = self.widgets["scout_textbuffer"]
        (iter_first, iter_last) = textbuffer.get_bounds()
        text = textbuffer.get_text(iter_first, iter_last, False)
        if text:
            q = ast.literal_eval(text)
            self.persp.chessfile.set_scout_filter(q)
            need_update = True

        if need_update and self.filtered:
            self.persp.gamelist.load_games()

    def ini_widgets_from_query(self, query):
        """ Set filter dialog widget values based on query dict key-value pairs """

        rule = "variant"
        if rule in query:
            index = 0
            model = self.widgets["variant"].get_model()
            for index, row in enumerate(model):
                if query[rule] == row[1]:
                    break
            self.widgets["variant"].set_active(index)

        for rule in ("white", "black", "event", "site", "date_from", "date_to", "eco_from", "eco_to", "annotator"):
            if rule in query:
                self.widgets[rule].set_text(query[rule])
            else:
                self.widgets[rule].set_text("")

        for rule in ("elo_from", "elo_to"):
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
            self.widgets["white_move"].set_text(", ".join(query["white-move"]))
        else:
            self.widgets["white_move"].set_text("")

        if "black-move" in query:
            self.widgets["black_move"].set_text(", ".join(query["black-move"]))
        else:
            self.widgets["black_move"].set_text("")

        moved = "moved" in query
        for piece in "pnbrqk":
            active = moved and piece.upper() in query["moved"]
            self.widgets["moved_%s" % piece].set_active(active)

        captured = "captured" in query
        for piece in "pnbrq":
            active = captured and piece.upper() in query["captured"]
            self.widgets["captured_%s" % piece].set_active(active)

        if captured and query["captured"] == "":
            self.widgets["captured_0"].set_active(True)
        else:
            self.widgets["captured_0"].set_active(False)

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
        self.board_control = BoardControl(self.setupmodel, {}, setup_position=True)
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

        textbuffer = self.widgets["scout_textbuffer"]
        textbuffer.set_text("")

    def get_queries_from_widgets(self):
        """ Build tag and scout query dict from filter dialog widget names and values """

        tag_query = {}
        material_query = {}
        pattern_query = {}

        tree_iter = self.widgets["variant"].get_active_iter()
        if tree_iter is not None:
            model = self.widgets["variant"].get_model()
            variant_code = model[tree_iter][1]
            tag_query["variant"] = variant_code

        for rule in ("white", "black", "event", "site", "date_from", "date_to", "eco_from", "eco_to", "annotator"):
            if self.widgets[rule].get_text():
                tag_query[rule] = self.widgets[rule].get_text()

        for rule in ("elo_from", "elo_to"):
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
            moves = [move.strip() for move in self.widgets["white_move"].get_text().split(",")]
            material_query["white-move"] = moves

        if self.widgets["black_move"].get_text():
            moves = [move.strip() for move in self.widgets["black_move"].get_text().split(",")]
            material_query["black-move"] = moves

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
            material_query["captured"] = "%s" % captured.replace("0", "")

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

    def on_copy_sub_fen(self, widget):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        text = self.widgets["sub_fen"].get_text()
        if len(text) > 0:
            clipboard.set_text(text, -1)

    def on_paste_sub_fen(self, widget):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        text = clipboard.wait_for_text()
        if text.count("/") == 7:
            self.board_control.emit("action", "SETUP", None, text)

    def game_changed(self, model, ply):
        GLib.idle_add(self.fen_changed)

    def get_fen(self):
        return self.setupmodel.boards[-1].as_fen(NORMALCHESS)

# -*- coding: UTF-8 -*-
from io import StringIO

from gi.repository import Gtk, GObject

from pychess.compat import create_task
from pychess.Utils.const import DRAW, LOCAL, WHITE, BLACK, WAITING_TO_START, reprResult, \
    UNDOABLE_STATES, FIRST_PAGE, PREV_PAGE, NEXT_PAGE
from pychess.Players.Human import Human
from pychess.Utils.GameModel import GameModel
from pychess.perspectives import perspective_manager
from pychess.Variants import variants
from pychess.Database.model import game, event, site, pl1, pl2
from pychess.widgets import newGameDialog
from pychess.Savers import pgn


cols = (game.c.id, pl1.c.name, game.c.white_elo, pl2.c.name, game.c.black_elo,
        game.c.result, game.c.date, event.c.name, site.c.name, game.c.round,
        game.c.ply_count, game.c.eco, game.c.time_control, game.c.variant, game.c.fen)


class GameList(Gtk.TreeView):
    def __init__(self, persp):
        GObject.GObject.__init__(self)
        self.persp = persp

        self.records = []
        self.preview_cid = None

        # GTK_SELECTION_BROWSE - exactly one item is always selected
        self.get_selection().set_mode(Gtk.SelectionMode.BROWSE)

        self.liststore = Gtk.ListStore(int, str, str, str, str, str, str, str,
                                       str, str, str, str, str, str, str)
        self.modelsort = Gtk.TreeModelSort(self.liststore)

        self.modelsort.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.modelsort.connect("sort-column-changed", self.sort_column_changed)
        self.set_model(self.modelsort)
        self.get_selection().set_mode(Gtk.SelectionMode.BROWSE)
        self.set_headers_visible(True)
        self.set_rules_hint(True)
        self.set_search_column(1)

        titles = (_("Id"), _("White"), _("W Elo"), _("Black"), _("B Elo"),
                  _("Result"), _("Date"), _("Event"), _("Site"), _("Round"),
                  _("Length"), "ECO", _("Time control"), _("Variant"), "FEN")

        for i, title in enumerate(titles):
            r = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, r, text=i)
            column.set_resizable(True)
            column.set_reorderable(True)
            column.set_sort_column_id(i)
            self.append_column(column)

        self.connect("row-activated", self.row_activated)

        self.set_cursor(0)
        self.columns_autosize()
        self.gamemodel = GameModel()
        self.ply = 0

        # buttons
        toolbar = Gtk.Toolbar()

        firstButton = Gtk.ToolButton(stock_id=Gtk.STOCK_MEDIA_PREVIOUS)
        firstButton.set_tooltip_text(_("First games"))
        toolbar.insert(firstButton, -1)

        prevButton = Gtk.ToolButton(stock_id=Gtk.STOCK_MEDIA_REWIND)
        prevButton.set_tooltip_text(_("Previous games"))
        toolbar.insert(prevButton, -1)

        nextButton = Gtk.ToolButton(stock_id=Gtk.STOCK_MEDIA_FORWARD)
        nextButton.set_tooltip_text(_("Next games"))
        toolbar.insert(nextButton, -1)

        firstButton.connect("clicked", self.on_first_clicked)
        prevButton.connect("clicked", self.on_prev_clicked)
        nextButton.connect("clicked", self.on_next_clicked)

        limit_combo = Gtk.ComboBoxText()
        for limit in ("100", "500", "1000", "5000"):
            limit_combo.append_text(limit)
        limit_combo.set_active(0)

        toolitem = Gtk.ToolItem.new()
        toolitem.add(limit_combo)
        toolbar.insert(toolitem, -1)
        limit_combo.connect("changed", self.on_limit_combo_changed)

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        sw.add(self)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.box.pack_start(sw, True, True, 0)
        self.box.pack_start(toolbar, False, False, 0)
        self.box.show_all()

    def on_first_clicked(self, button):
        self.load_games(direction=FIRST_PAGE)

    def on_prev_clicked(self, button):
        self.load_games(direction=PREV_PAGE)

    def on_next_clicked(self, button):
        self.load_games(direction=NEXT_PAGE)

    def on_limit_combo_changed(self, combo):
        text = combo.get_active_text()
        if text is not None:
            self.persp.chessfile.limit = int(text)
            self.load_games(direction=FIRST_PAGE)

    def sort_column_changed(self, treesortable):
        sort_column_id, order = treesortable.get_sort_column_id()
        if sort_column_id is None:
            self.modelsort.set_sort_column_id(0, Gtk.SortType.ASCENDING)
            sort_column_id, order = 0, Gtk.SortType.ASCENDING

        self.set_search_column(sort_column_id)
        is_desc = order == Gtk.SortType.DESCENDING
        self.persp.chessfile.set_tag_order(cols[sort_column_id], is_desc)
        self.load_games(direction=FIRST_PAGE)

    def load_games(self, direction=FIRST_PAGE):
        selection = self.get_selection()
        if selection is not None and self.preview_cid is not None and \
                selection.handler_is_connected(self.preview_cid):
            with GObject.signal_handler_block(selection, self.preview_cid):
                self.liststore.clear()
        else:
            self.liststore.clear()

        add = self.liststore.append

        self.records = []
        records, plys = self.persp.chessfile.get_records(direction)
        for i, rec in enumerate(records):
            game_id = rec["Id"]
            offs = rec["Offset"]
            wname = rec["White"]
            bname = rec["Black"]
            welo = rec["WhiteElo"]
            belo = rec["BlackElo"]
            result = rec["Result"]
            result = "½-½" if result == DRAW else reprResult[result] if result else "*"
            event = "" if rec["Event"] is None else rec["Event"].replace("?", "")
            site = "" if rec["Site"] is None else rec["Site"].replace("?", "")
            round_ = "" if rec["Round"] is None else rec["Round"].replace("?", "")
            date = "" if rec["Date"] is None else rec["Date"].replace(".??", "").replace("????.", "")

            try:
                ply = rec["PlyCount"]
                length = str(int(ply) // 2) if ply else ""
            except ValueError:
                length = ""
            eco = rec["ECO"]
            tc = rec["TimeControl"]
            variant = rec["Variant"]
            variant = variants[variant].cecp_name.capitalize() if variant else ""
            fen = rec["FEN"]

            add([game_id, wname, welo, bname, belo, result, date, event, site,
                 round_, length, eco, tc, variant, fen])

            ply = plys.get(offs) if offs in plys else 0
            self.records.append((rec, ply))

        self.set_cursor(0)

    def get_record(self, path):
        if path is None:
            return None, None
        else:
            return self.records[self.modelsort.convert_path_to_child_path(path)[0]]

    def row_activated(self, widget, path, col):
        rec, ply = self.get_record(path)
        if rec is None:
            return

        # Enable unfinished games to continue from newgamedialog
        if rec["Result"] not in UNDOABLE_STATES:
            newGameDialog.EnterNotationExtension.run()
            model = self.persp.chessfile.loadToModel(rec)
            text = pgn.save(StringIO(), model)
            newGameDialog.EnterNotationExtension.sourcebuffer.set_text(text)
            return

        self.gamemodel = GameModel()

        variant = rec["Variant"]
        if variant:
            self.gamemodel.tags["Variant"] = variant

        # Lichess exports study .pgn without White and Black tags
        wp = "" if rec["White"] is None else rec["White"]
        bp = "" if rec["Black"] is None else rec["Black"]
        p0 = (LOCAL, Human, (WHITE, wp), wp)
        p1 = (LOCAL, Human, (BLACK, bp), bp)
        self.persp.chessfile.loadToModel(rec, -1, self.gamemodel)

        self.gamemodel.endstatus = self.gamemodel.status if self.gamemodel.status in UNDOABLE_STATES else None
        self.gamemodel.status = WAITING_TO_START

        perspective_manager.activate_perspective("games")
        perspective = perspective_manager.get_perspective("games")
        create_task(perspective.generalStart(self.gamemodel, p0, p1))

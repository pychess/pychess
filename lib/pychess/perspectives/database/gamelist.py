# -*- coding: UTF-8 -*-
from __future__ import print_function

from gi.repository import Gtk, GObject

from pychess.Utils.const import DRAW, LOCAL, WHITE, BLACK, WAITING_TO_START, reprResult
from pychess.Players.Human import Human
from pychess.widgets.ionest import game_handler
from pychess.Utils.GameModel import GameModel
from pychess.perspectives import perspective_manager
from pychess.Utils.IconLoader import load_icon

media_previous = load_icon(16, "gtk-media-previous-ltr", "media-skip-backward")
media_rewind = load_icon(16, "gtk-media-rewind-ltr", "media-seek-backward")
media_forward = load_icon(16, "gtk-media-forward-ltr", "media-seek-forward")
media_next = load_icon(16, "gtk-media-next-ltr", "media-skip-forward")


def createImage(pixbuf):
    image = Gtk.Image()
    image.set_from_pixbuf(pixbuf)
    return image


class GameList(Gtk.TreeView):
    LIMIT = 500

    def __init__(self, chessfile):
        GObject.GObject.__init__(self)
        self.chessfile = chessfile
        self.chessfiles = [self.chessfile, ]

        persp = perspective_manager.get_perspective("database")
        persp.connect("chessfile_opened", self.on_chessfile_opened)
        persp.connect("chessfile_closed", self.on_chessfile_closed)

        self.preview_cid = None
        self.opening_tree_cid = None

        # GTK_SELECTION_BROWSE - exactly one item is always selected
        self.get_selection().set_mode(Gtk.SelectionMode.BROWSE)

        self.offset = 0

        self.liststore = Gtk.ListStore(int, str, str, str, str, str, str, str,
                                       str, str, str, str, str, str, str)
        self.modelsort = Gtk.TreeModelSort(self.liststore)

        self.modelsort.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.set_model(self.modelsort)
        self.get_selection().set_mode(Gtk.SelectionMode.BROWSE)
        self.set_headers_visible(True)
        self.set_rules_hint(True)
        self.set_fixed_height_mode(True)
        self.set_search_column(1)

        cols = (_("Id"), _("White"), _("W Elo"), _("Black"), _("B Elo"),
                _("Result"), _("Date"), _("Event"), _("Site"), _("Round"),
                _("Length"), "ECO", "TC", "Variant", "FEN")
        for i, col in enumerate(cols):
            r = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col, r, text=i)
            column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            column.set_resizable(True)
            column.set_reorderable(True)
            column.set_sort_column_id(i)
            column.connect("clicked", self.column_clicked, i)
            self.append_column(column)

        self.connect("row-activated", self.row_activated)

        self.set_cursor(0)
        self.columns_autosize()
        self.gameno = 0
        self.gamemodel = None
        self.ply = 0

        #  buttons
        startbut = Gtk.Button()
        startbut.add(createImage(media_previous))

        backbut = Gtk.Button()
        backbut.add(createImage(media_rewind))

        forwbut = Gtk.Button()
        forwbut.add(createImage(media_forward))

        endbut = Gtk.Button()
        endbut.add(createImage(media_next))

        button_box = Gtk.Box()

        self.label = Gtk.Label(_("Empty"))

        button_box.pack_start(startbut, True, True, 0)
        button_box.pack_start(backbut, True, True, 0)
        button_box.pack_start(self.label, True, True, 0)
        button_box.pack_start(forwbut, True, True, 0)
        button_box.pack_start(endbut, True, True, 0)

        startbut.connect("clicked", self.on_start_button)
        backbut.connect("clicked", self.on_back_button)
        forwbut.connect("clicked", self.on_forward_button)
        endbut.connect("clicked", self.on_end_button)

        self.progress_dock = Gtk.Alignment()
        button_box.pack_start(self.progress_dock, True, True, 0)

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        sw.add(self)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.box.pack_start(sw, True, True, 0)
        self.box.pack_start(button_box, False, False, 0)
        self.box.show_all()

    def on_chessfile_opened(self, persp, chessfile):
        self.chessfile = chessfile
        self.chessfiles.append(self.chessfile)
        self.load_games()

    def on_chessfile_closed(self, persp):
        if len(self.chessfiles) == 1:
            self.chessfiles.remove(self.chessfile)
            self.chessfile.close()
            perspective_manager.disable_perspective("database")

        elif self.chessfile.path is not None:
            self.chessfiles.remove(self.chessfile)
            self.chessfile.close()

    def on_start_button(self, widget):
        self.offset = 0
        self.load_games()

    def on_back_button(self, widget):
        if self.offset - self.LIMIT >= 0:
            self.offset = self.offset - self.LIMIT
            self.load_games()

    def on_forward_button(self, widget):
        if self.offset + self.LIMIT < self.chessfile.count:
            self.offset = self.offset + self.LIMIT
            self.load_games()

    def on_end_button(self, widget):
        if self.offset + self.LIMIT == self.chessfile.count:
            return
        if self.chessfile.count % self.LIMIT == 0:
            self.offset = self.chessfile.count - self.LIMIT
        else:
            self.offset = (self.chessfile.count // self.LIMIT) * self.LIMIT
        self.load_games()

    def column_clicked(self, col, data):
        self.set_search_column(data)

    def load_games(self):
        selection = self.get_selection()
        if selection is not None and self.preview_cid is not None and \
                selection.handler_is_connected(self.preview_cid):
            with GObject.signal_handler_block(selection, self.preview_cid):
                self.liststore.clear()
        else:
            self.liststore.clear()

        getTag = self.chessfile._getTag
        getResult = self.chessfile.get_result
        getPlayers = self.chessfile.get_player_names
        add = self.liststore.append

        self.chessfile.get_records(self.offset, self.LIMIT)

        self.id_list = []
        for i in range(len(self.chessfile.games)):
            game_id = self.chessfile.get_id(i)
            self.id_list.append(game_id)
            wname, bname = getPlayers(i)
            welo = getTag(i, "WhiteElo")
            belo = getTag(i, "BlackElo")
            result = getResult(i)
            result = "½-½" if result == DRAW else reprResult[result]
            event = getTag(i, 'Event')
            site = getTag(i, 'Site')
            round_ = getTag(i, "Round")
            date = getTag(i, "Date")
            ply = getTag(i, "PlyCount")
            length = str(int(ply) // 2) if ply else ""
            eco = getTag(i, "ECO")
            tc = getTag(i, "TimeControl")
            variant = getTag(i, "Variant")
            fen = getTag(i, "FEN")
            add([game_id, wname, welo, bname, belo, result, date, event, site,
                 round_, length, eco, tc, variant, fen])

        self.set_cursor(0)
        self.update_count()

    def row_activated(self, widget, path, col):
        game_id = self.liststore[self.modelsort.convert_path_to_child_path(path)[0]][0]
        gameno = self.id_list.index(game_id)

        self.gamemodel = GameModel()

        variant = self.chessfile.get_variant(gameno)
        if variant:
            self.gamemodel.tags["Variant"] = variant

        wp, bp = self.chessfile.get_player_names(gameno)
        p0 = (LOCAL, Human, (WHITE, wp), wp)
        p1 = (LOCAL, Human, (BLACK, bp), bp)
        self.chessfile.loadToModel(gameno, -1, self.gamemodel)

        self.gamemodel.status = WAITING_TO_START
        game_handler.generalStart(self.gamemodel, p0, p1)

        perspective_manager.activate_perspective("games")

    def update_count(self):
        self.chessfile.update_count()
        self.label.set_text("%s - %s / %s" % (self.offset, self.offset + self.LIMIT, self.chessfile.count))
        self.label.show()

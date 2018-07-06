from gi.repository import Gtk, Gdk

from pychess.System import conf
from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import BLACK
from pychess.Utils.Move import toSAN, toFAN
from pychess.widgets.Background import hexcol

__title__ = _("Move History")
__active__ = True
__icon__ = addDataPrefix("glade/panel_moves.svg")
__desc__ = _(
    "The moves sheet keeps track of the players' moves and lets you navigate through the game history")


class Sidepanel:
    def load(self, gmwidg):

        self.gamemodel = gmwidg.board.view.model
        self.model_cids = [
            self.gamemodel.connect_after("game_changed", self.game_changed),
            self.gamemodel.connect_after("game_started", self.game_started),
            self.gamemodel.connect_after("moves_undone", self.moves_undone),
            self.gamemodel.connect_after("game_terminated", self.on_game_terminated),
        ]

        self.tv = Gtk.TreeView()
        self.tv.set_headers_visible(False)
        self.tv.set_grid_lines(True)
        self.tv.set_activate_on_single_click(True)
        self.tv.get_selection().set_mode(Gtk.SelectionMode.NONE)
        self.activated_cell = (None, None)

        def is_row_separator(treemodel, treeiter):
            mvcount, wmove, bmove, row, wbg, bbg = self.store[treeiter]
            return row == 0
        self.tv.set_row_separator_func(is_row_separator)

        self.tv.connect("style-updated", self.on_style_updated)
        movetext_font = conf.get("movetextFont")

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("mvcount", renderer, text=0)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.tv.append_column(column)

        self.white_renderer = Gtk.CellRendererText()
        self.white_renderer.set_property("xalign", 1)
        self.white_renderer.set_property("font", movetext_font)
        self.white_column = Gtk.TreeViewColumn("white", self.white_renderer, text=1, background=4)
        self.white_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.tv.append_column(self.white_column)

        self.black_renderer = Gtk.CellRendererText()
        self.black_renderer.set_property("xalign", 1)
        self.black_renderer.set_property("font", movetext_font)
        self.black_column = Gtk.TreeViewColumn("black", self.black_renderer, text=2, background=5)
        self.black_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.tv.append_column(self.black_column)

        # To prevent black moves column expand to the right we add a dummy column finally
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("dummy", renderer)
        self.tv.append_column(column)

        scrollwin = Gtk.ScrolledWindow()
        scrollwin.add(self.tv)

        # Our liststore elements will be:
        # mvcount, white move, black move, row number, white move background, black move background
        self.store = Gtk.ListStore(str, str, str, int, str, str)
        self.tv.set_model(self.store)
        self.tv_cid = self.tv.connect('row_activated', self.on_row_activated)

        self.boardview = gmwidg.board.view
        self.cid = self.boardview.connect("shownChanged", self.shownChanged)
        scrollwin.show_all()

        self.figuresInNotation = conf.get("figuresInNotation")

        def figuresInNotationCallback(none):
            game = self.boardview.model
            if game.lesson_game:
                return

            self.figuresInNotation = conf.get("figuresInNotation")

            for i, move in enumerate(game.moves):
                board = game.variations[0][i]
                ply = game.lowply + i + 1
                if conf.get("figuresInNotation"):
                    notat = toFAN(board, move)
                else:
                    notat = toSAN(board, move, True)

                row, column = self.ply_to_row_col(ply)

                col = 2 if column == self.black_column else 1
                treeiter = self.store.get_iter(Gtk.TreePath(row))
                self.store.set_value(treeiter, col, notat)

        def font_changed(none):
            movetext_font = conf.get("movetextFont")
            self.black_renderer.set_property("font", movetext_font)
            self.white_renderer.set_property("font", movetext_font)
            self.shownChanged(self.boardview, self.boardview.shown)

        self.cids_conf = []
        self.cids_conf.append(conf.notify_add("movetextFont", font_changed))
        self.cids_conf.append(conf.notify_add("figuresInNotation", figuresInNotationCallback))

        return scrollwin

    def get_background_rgba(self, selected=False):
        if selected:
            found, color = self.tv.get_style_context().lookup_color("theme_selected_bg_color")
        else:
            found, color = self.tv.get_style_context().lookup_color("theme_base_color")
        return hexcol(Gdk.RGBA(color.red, color.green, color.blue, 1))

    def on_style_updated(self, widget):
        for row in self.store:
            row[4] = self.get_background_rgba()
            row[5] = self.get_background_rgba()
        # update selected cell
        self.shownChanged(self.boardview, self.boardview.shown)

    def on_game_terminated(self, model):
        self.tv.disconnect(self.tv_cid)
        for cid in self.model_cids:
            self.gamemodel.disconnect(cid)
        self.boardview.disconnect(self.cid)
        for cid in self.cids_conf:
            conf.notify_remove(cid)

    def on_row_activated(self, tv, path, col, from_show_changed=False):
        if col not in (self.white_column, self.black_column):
            return

        # Make previous activated cell background color unselected
        old_row, old_col = self.activated_cell
        if old_row is not None:
            bg_col = 5 if old_col == self.black_column else 4
            treeiter = self.store.get_iter(Gtk.TreePath(old_row))
            self.store.set_value(treeiter, bg_col, self.get_background_rgba(selected=False))

        # Make activated cell background color selected
        self.activated_cell = path[0], col
        bg_col = 5 if col == self.black_column else 4
        treeiter = self.store.get_iter(Gtk.TreePath(path[0]))
        self.store.set_value(treeiter, bg_col, self.get_background_rgba(selected=True))

        index = path[0] * 2 - 1 + (1 if col == self.black_column else 0)
        if self.gamemodel.starting_color == BLACK:
            index -= 1

        if index < len(self.gamemodel.boards):
            # Don't set shown board if on_row_activated() was called from shownChanged()
            if not from_show_changed:
                board = self.gamemodel.boards[index]
                self.boardview.setShownBoard(board)

    def shownChanged(self, boardview, shown):
        if boardview is None or self.gamemodel is None:
            return
        if not boardview.shownIsMainLine():
            return

        row, column = self.ply_to_row_col(shown)

        try:
            self.on_row_activated(self, Gtk.TreePath(row), column, from_show_changed=True)
            self.tv.scroll_to_cell(row)
        except ValueError:
            pass
            # deleted variations by moves_undoing

    def moves_undone(self, gamemodel, moves):
        for i in range(moves):
            treeiter = self.store.get_iter((len(self.store) - 1, ))
            # If latest move is black move don't remove whole line!
            if self.store[-1][2]:
                self.store.set_value(treeiter, 2, "")
            else:
                self.store.remove(treeiter)

    def game_changed(self, gamemodel, ply):
        if self.boardview is None or self.boardview.model is None:
            return

        if len(self.store) == 0:
            for i in range(len(self.store) + gamemodel.lowply, ply + 1):
                self.add_move(gamemodel, i)
        else:
            self.add_move(gamemodel, ply)

        self.shownChanged(self.boardview, ply)

    def game_started(self, game):
        if game.lesson_game:
            return
        self.game_changed(game, game.ply)

    def add_move(self, gamemodel, ply):
        if ply == gamemodel.lowply:
            self.store.append(["%4s." % gamemodel.lowply, "1234567", "1234567", 0, self.get_background_rgba(), self.get_background_rgba()])
            return

        if self.figuresInNotation:
            notat = toFAN(gamemodel.getBoardAtPly(ply - 1), gamemodel.getMoveAtPly(ply - 1))
        else:
            notat = toSAN(gamemodel.getBoardAtPly(ply - 1), gamemodel.getMoveAtPly(ply - 1), localRepr=True)

        row, column = self.ply_to_row_col(ply)

        if len(self.store) - 1 < row:
            mvcount = "%s." % ((ply + 1) // 2)
            if column == self.white_column:
                self.store.append([mvcount, notat, "", row, self.get_background_rgba(), self.get_background_rgba()])
            else:
                self.store.append([mvcount, "", notat, row, self.get_background_rgba(), self.get_background_rgba()])
        else:
            treeiter = self.store.get_iter(Gtk.TreePath(row))
            col = 1 if column == self.white_column else 2
            self.store.set_value(treeiter, col, notat)

    def ply_to_row_col(self, ply):
        col = ply & 1 and self.white_column or self.black_column
        if self.gamemodel.lowply & 1:
            row = (ply - self.gamemodel.lowply) // 2
        else:
            row = (ply - self.gamemodel.lowply - 1) // 2
        return row + 1, col

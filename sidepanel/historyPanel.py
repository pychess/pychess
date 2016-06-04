from gi.repository import Gtk

from pychess.System import conf
from pychess.System.idle_add import idle_add
from pychess.System.prefix import addDataPrefix
from pychess.Utils.Move import toSAN, toFAN

__title__ = _("Move History")
__active__ = True
__icon__ = addDataPrefix("glade/panel_moves.svg")
__desc__ = _(
    "The moves sheet keeps track of the players' moves and lets you navigate through the game history")


class Switch:
    def __init__(self):
        self.on = False

    def __enter__(self):
        self.on = True

    def __exit__(self, *a):
        self.on = False


class Sidepanel:
    def __init__(self):
        self.frozen = Switch()

    def load(self, gmwidg):
        __widget__ = Gtk.ScrolledWindow()
        __widget__.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.numbers = Gtk.TreeView()
        self.numbers.set_property("can_focus", False)
        self.numbers.set_property("sensitive", False)
        self.numbers.set_property("width_request", 35)
        self.left = Gtk.TreeView()
        self.numbers.set_property("width_request", 60)
        self.right = Gtk.TreeView()
        self.numbers.set_property("width_request", 60)

        box = Gtk.Box(spacing=0)
        box.pack_start(self.numbers, False, True, 0)
        box.pack_start(self.left, True, True, 0)
        box.pack_start(self.right, True, True, 0)

        port = Gtk.Viewport()
        port.add(box)
        port.set_shadow_type(Gtk.ShadowType.NONE)

        __widget__.add(port)
        __widget__.show_all()

        self.cids = {}
        self.boardview = gmwidg.board.view

        self.model_cids = [
            self.boardview.model.connect_after("game_changed", self.game_changed),
            self.boardview.model.connect_after("game_started", self.game_started),
            self.boardview.model.connect_after("moves_undone", self.moves_undone),
            self.boardview.model.connect_after("game_terminated", self.on_game_terminated),
        ]
        self.cids[self.boardview] = self.boardview.connect("shownChanged", self.shownChanged)

        # Initialize treeviews

        def fixList(list, xalign=0):
            list.set_property("headers_visible", False)
            list.set_property("rules_hint", True)
            list.set_model(Gtk.ListStore(str))
            renderer = Gtk.CellRendererText()
            renderer.set_property("xalign", xalign)
            list.append_column(Gtk.TreeViewColumn(None, renderer, text=0))
            list.get_selection().set_mode(Gtk.SelectionMode.SINGLE)

        fixList(self.numbers, 1)
        fixList(self.left, 0)
        fixList(self.right, 0)

        self.cids[self.left] = self.left.connect('cursor_changed', self.cursorChanged, self.left, 0)
        self.cids[self.right] = self.right.connect('cursor_changed', self.cursorChanged, self.right, 1)

        # Lock scrolling

        self.adjustment = __widget__.get_vadjustment()

        def changed(vadjust):
            if not hasattr(vadjust, "need_scroll") or vadjust.need_scroll:
                vadjust.set_value(vadjust.get_upper() - vadjust.get_page_size(
                ))
                vadjust.need_scroll = True

        self.adj_cid1 = self.adjustment.connect("changed", changed)

        def value_changed(vadjust):
            vadjust.need_scroll = abs(vadjust.get_value() + vadjust.get_page_size() -
                                      vadjust.get_upper()) < vadjust.get_step_increment()

        self.adj_cid2 = self.adjustment.connect("value-changed", value_changed)

        # Connect to preferences

        def figuresInNotationCallback(none):
            game = self.boardview.model
            for board, move in zip(game.variations[0], game.moves):
                if conf.get("figuresInNotation", False):
                    notat = toFAN(board, move)
                else:
                    notat = toSAN(board, move, True)
                row, col, other = self._ply_to_row_col_other(board.ply + 1)
                iter = col.get_model().get_iter((row, ))
                col.get_model().set(iter, 0, notat)

        self.conf_conid = conf.notify_add("figuresInNotation", figuresInNotationCallback)

        # Return

        return __widget__

    def on_game_terminated(self, model):
        conf.notify_remove(self.conf_conid)
        self.adjustment.disconnect(self.adj_cid1)
        self.adjustment.disconnect(self.adj_cid2)
        for cid in self.model_cids:
            self.boardview.model.disconnect(cid)
        for obj in self.cids:
            obj.disconnect(self.cids[obj])
        self.cids = {}

    def cursorChanged(self, widget, tree, col):
        if self.frozen.on:
            return

        path, focus_column = tree.get_cursor()
        indices = path.get_indices()
        row = indices[0]

        if self.boardview.model.lowply & 1:
            ply = row * 2 + col
        else:
            ply = row * 2 + col + 1

        board = self.boardview.model.boards[ply]
        self.boardview.setShownBoard(board)

    @idle_add
    def moves_undone(self, game, moves):
        with self.frozen:
            for i in reversed(range(moves)):
                try:
                    row, view, other = self._ply_to_row_col_other(
                        game.variations[0][-1].ply + moves - i)
                    model = view.get_model()
                    model.remove(model.get_iter((row, )))
                    if view == self.left:
                        model = self.numbers.get_model()
                        model.remove(model.get_iter((row, )))
                except ValueError:
                    continue

    @idle_add
    def game_changed(self, game, ply):
        if self.boardview is None or self.boardview.model is None:
            return
        left_model = self.left.get_model()
        right_model = self.right.get_model()
        if left_model is None or right_model is None:
            return

        len_ = len(left_model) + len(right_model) + 1
        if len(left_model) and not left_model[0][0]:
            len_ -= 1
        for i in range(len_ + game.lowply, ply + 1):
            self.__addMove(game, i)
        self.shownChanged(self.boardview, ply)

    def game_started(self, game):
        self.game_changed(game, game.ply)

    def __addMove(self, game, ply):
        # print "Am I doing anything?"
        row, view, other = self._ply_to_row_col_other(ply)

        if conf.get("figuresInNotation", False):
            notat = toFAN(
                game.getBoardAtPly(ply - 1), game.getMoveAtPly(ply - 1))
        else:
            notat = toSAN(
                game.getBoardAtPly(ply - 1),
                game.getMoveAtPly(ply - 1),
                localRepr=True)

        # Test if the row is 'filled'
        if len(view.get_model()) == len(self.numbers.get_model()):
            num = str((ply + 1) // 2) + "."
            self.numbers.get_model().append([num])

        # Test if the move is black first move. This will be the case if the
        # game was loaded from a fen/epd starting at black
        if view == self.right and len(view.get_model()) == len(other.get_model(
        )):
            self.left.get_model().append([""])

        view.get_model().append([notat])

    @idle_add
    def shownChanged(self, boardview, shown):
        if self.boardview is None or self.boardview.model is None:
            return
        if not self.boardview.shownIsMainLine():
            return
        if shown <= self.boardview.model.lowply:
            # print "Or is it me?"
            self.left.get_selection().unselect_all()
            self.right.get_selection().unselect_all()
            return

        row, col, other = self._ply_to_row_col_other(shown)

        with self.frozen:
            other.get_selection().unselect_all()
            try:
                col.get_selection().select_iter(col.get_model().get_iter(row))
                col.scroll_to_cell((row, ), None, False)
            except ValueError:
                pass
                # deleted variations by moves_undoing

    def _ply_to_row_col_other(self, ply):
        col = ply & 1 and self.left or self.right
        other = ply & 1 and self.right or self.left
        if self.boardview.model.lowply & 1:
            row = (ply - self.boardview.model.lowply) // 2
        else:
            row = (ply - self.boardview.model.lowply - 1) // 2
        return row, col, other

from gi.repository import Gtk, GLib, GdkPixbuf

from pychess.ic.FICSObjects import FICSGame, get_player_tooltip_text
from pychess.ic import TYPE_BLITZ, TYPE_LIGHTNING, TYPE_STANDARD, RATING_TYPES, \
    TYPE_BULLET, TYPE_ONE_MINUTE, TYPE_THREE_MINUTE, TYPE_FIVE_MINUTE, \
    TYPE_FIFTEEN_MINUTE, TYPE_FORTYFIVE_MINUTE
from pychess.Utils.IconLoader import load_icon, get_pixbuf
from pychess.System.Log import log
from pychess.System import conf, uistuff
from pychess.System.prefix import addDataPrefix
from pychess.perspectives.fics.ParrentListSection import ParrentListSection, cmp, \
    SEPARATOR, FOLLOW, FINGER, ARCHIVED, OBSERVE


__title__ = _("Game List")

__icon__ = addDataPrefix("glade/panel_games.svg")

__desc__ = _("List of ongoing games")


class Sidepanel(ParrentListSection):

    def load(self, widgets, connection, lounge):
        self.widgets = widgets
        self.connection = connection
        self.lounge = lounge

        __widget__ = lounge.games_list

        self.games = {}
        self.recpix = load_icon(16, "media-record")
        self.clearpix = get_pixbuf("glade/board.png")
        self.tv = self.widgets["gametreeview"]
        self.store = Gtk.ListStore(FICSGame, GdkPixbuf.Pixbuf, str, int, str,
                                   int, str, str)

        self.game_filter = self.store.filter_new()
        self.game_filter.set_visible_func(self.game_filter_func)

        self.filter_toggles = {}
        self.filter_buttons = ("standard_toggle", "blitz_toggle", "lightning_toggle", "variant_toggle")
        for widget in self.filter_buttons:
            uistuff.keep(self.widgets[widget], widget)
            self.widgets[widget].connect("toggled", self.on_filter_button_toggled)
            initial = conf.get(widget)
            self.filter_toggles[widget] = initial
            self.widgets[widget].set_active(initial)

        self.model = self.game_filter.sort_new_with_model()
        self.tv.set_model(self.model)
        self.tv.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.addColumns(self.tv,
                        "FICSGame",
                        "",
                        _("White"),
                        _("Rating"),
                        _("Black"),
                        _("Rating"),
                        _("Type"),
                        _("Rated"),
                        hide=[0],
                        pix=[1])

        self.tv.get_model().set_sort_func(0, self.pixCompareFunction, 1)
        for i in range(1, 7):
            self.tv.get_model().set_sort_func(i, self.compareFunction, i)
        self.prev_sort_column_id = []
        self.model.connect("sort-column-changed", self.on_sort_column_change)

        self.tv.set_has_tooltip(True)
        self.tv.connect("query-tooltip", self.on_query_tooltip)
        self.selection = self.tv.get_selection()
        self.selection.connect("changed", self.onSelectionChanged)
        self.onSelectionChanged(self.selection)

        try:
            self.tv.set_search_position_func(self.lowLeftSearchPosFunc, None)
        except AttributeError:
            # Unknow signal name is raised by gtk < 2.10
            pass

        def searchCallback(model, column, key, sel_iter, user_data):
            if model.get_value(sel_iter, 2).lower().startswith(key) or \
                    model.get_value(sel_iter, 4).lower().startswith(key):
                return False
            return True

        self.tv.set_search_equal_func(searchCallback, None)

        self.connection.games.connect("FICSGameCreated", self.onGameAdd)
        self.connection.games.connect("FICSGameEnded", self.onGameRemove)
        self.widgets["observeButton"].connect("clicked", self.on_observe)
        self.tv.connect("row-activated", self.on_observe)
        self.connection.bm.connect("obsGameCreated", self.onGameObserved)
        self.connection.bm.connect("obsGameUnobserved", self.onGameUnobserved)

        self.tv.connect('button-press-event', self.button_press_event)
        self.createLocalMenu((OBSERVE, FOLLOW, SEPARATOR, FINGER, ARCHIVED))

        return __widget__

    def game_filter_func(self, model, iter, data):
        game = model[iter][0]
        is_standard = game.game_type.rating_type in (TYPE_STANDARD, TYPE_FIFTEEN_MINUTE, TYPE_FORTYFIVE_MINUTE)
        is_blitz = game.game_type.rating_type in (TYPE_BLITZ, TYPE_THREE_MINUTE, TYPE_FIVE_MINUTE)
        is_lightning = game.game_type.rating_type in (TYPE_LIGHTNING, TYPE_BULLET, TYPE_ONE_MINUTE)
        is_variant = game.game_type.rating_type in RATING_TYPES[9:]
        return (
            self.filter_toggles["standard_toggle"] and is_standard) or (
            self.filter_toggles["blitz_toggle"] and is_blitz) or (
            self.filter_toggles["lightning_toggle"] and is_lightning) or (
            self.filter_toggles["variant_toggle"] and is_variant)

    def on_filter_button_toggled(self, widget):
        for button in self.filter_buttons:
            self.filter_toggles[button] = self.widgets[button].get_active()
        self.game_filter.refilter()

    # Multi-column sort based on TreeModelSortUtil from
    # https://github.com/metomi/rose/blob/master/lib/python/rose/gtk/util.py
    def on_sort_column_change(self, model):
        """ Store previous sorting information for multi-column sorts. """
        id, order = self.tv.get_model().get_sort_column_id()
        if id is None and order is None:
            return False
        if (self.prev_sort_column_id and self.prev_sort_column_id[0][0] == id):
            self.prev_sort_column_id.pop(0)
        self.prev_sort_column_id.insert(0, (id, order))
        if len(self.prev_sort_column_id) > 2:
            self.prev_sort_column_id.pop()

    def compareFunction(self, model, iter0, iter1, column):
        """ Multi-column sort. """
        val0 = model.get_value(iter0, column)
        val1 = model.get_value(iter1, column)
        rval = cmp(val0, val1)
        # If rval is 1 or -1, no need for a multi-column sort.
        if rval == 0:
            this_order = self.tv.get_model().get_sort_column_id()[1]
            cmp_factor = 1
            if this_order == Gtk.SortType.DESCENDING:
                # We need to de-invert the sort order for multi sorting.
                cmp_factor = -1
        i = 0
        while rval == 0 and i < len(self.prev_sort_column_id):
            next_id, next_order = self.prev_sort_column_id[i]
            if next_id == column:
                i += 1
                continue
            next_cmp_factor = cmp_factor * 1
            if next_order == Gtk.SortType.DESCENDING:
                # Set the correct order for multi sorting.
                next_cmp_factor = cmp_factor * -1
            val0 = model.get_value(iter0, next_id)
            val1 = model.get_value(iter1, next_id)
            rval = next_cmp_factor * cmp(val0, val1)
            i += 1
        return rval

    def on_query_tooltip(self, widget, x, y, keyboard_tip, tooltip):
        if not widget.get_tooltip_context(x, y, keyboard_tip):
            return False
        bool, wx, wy, model, path, sel_iter = widget.get_tooltip_context(
            x, y, keyboard_tip)
        bin_x, bin_y = widget.convert_widget_to_bin_window_coords(x, y)
        result = widget.get_path_at_pos(bin_x, bin_y)

        if result is not None:
            path, column, cell_x, cell_y = result
            for player, column_number in ((self.model[path][0].wplayer, 1),
                                          (self.model[path][0].bplayer, 3)):
                if column is self.tv.get_column(column_number):
                    tooltip.set_text(
                        get_player_tooltip_text(player,
                                                show_status=False))
                    widget.set_tooltip_cell(tooltip, path, None, None)
                    return True
        return False

    def onSelectionChanged(self, selection):
        model, paths = selection.get_selected_rows()
        a_selected_game_is_observable = False
        for path in paths:
            rowiter = model.get_iter(path)
            game = model.get_value(rowiter, 0)
            if not game.private and game.supported:
                a_selected_game_is_observable = True
                break
        self.widgets["observeButton"].set_sensitive(
            a_selected_game_is_observable)

    def _update_gamesrunning_label(self):
        count = len(self.games)
        self.widgets["gamesRunningLabel"].set_text(_("Games running: %d") %
                                                   count)

    def onGameAdd(self, games, new_games):
        game_store = {}
        for game in new_games:
            game_store[game] = (game, self.clearpix,
                                game.wplayer.name + game.wplayer.display_titles(),
                                game.wplayer.getRatingForCurrentGame(),
                                game.bplayer.name + game.bplayer.display_titles(),
                                game.bplayer.getRatingForCurrentGame(),
                                game.display_text, game.display_rated)

        def do_onGameAdd(games, new_games, game_store):
            for game in new_games:
                # game removed before we finish processing "games /bslwBzSLx"
                if game not in game_store:
                    continue
                # log.debug("%s" % game,
                # extra={"task": (self.connection.username, "GTS.onGameAdd")})
                ti = self.store.append(game_store[game])
                self.games[game] = {"ti": ti}
                self.games[game]["private_cid"] = game.connect(
                    "notify::private", self.private_changed)
                self._update_gamesrunning_label()

        GLib.idle_add(do_onGameAdd,
                      games,
                      new_games,
                      game_store,
                      priority=GLib.PRIORITY_LOW)

    def private_changed(self, game, prop):
        try:
            self.store.set(self.games[game]["ti"], 6, game.display_text)
        except KeyError:
            pass
        self.onSelectionChanged(self.tv.get_selection())
        return False

    def onGameRemove(self, games, game):
        def do_onGameRemove(games, game):
            log.debug(
                "%s" % game,
                extra={"task": (self.connection.username, "GTS.onGameRemove")})
            if game not in self.games:
                return
            if self.store.iter_is_valid(self.games[game]["ti"]):
                self.store.remove(self.games[game]["ti"])
            if game.handler_is_connected(self.games[game]["private_cid"]):
                game.disconnect(self.games[game]["private_cid"])
            del self.games[game]
            self._update_gamesrunning_label()

        GLib.idle_add(do_onGameRemove, games, game, priority=GLib.PRIORITY_LOW)

    def onGameObserved(self, bm, game):
        if game in self.games:
            treeiter = self.games[game]["ti"]
            self.store.set_value(treeiter, 1, self.recpix)

    def onGameUnobserved(self, bm, game):
        if game in self.games:
            treeiter = self.games[game]["ti"]
            self.store.set_value(treeiter, 1, self.clearpix)

    def getSelectedPlayer(self):
        model = self.tv.get_model()
        path, col = self.tv.get_cursor()
        col_index = self.tv.get_columns().index(col)
        game = model.get_value(model.get_iter(path), 0)
        return game.bplayer if col_index >= 3 else game.wplayer

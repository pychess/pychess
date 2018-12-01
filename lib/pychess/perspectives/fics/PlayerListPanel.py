from gi.repository import Gtk, GLib, GdkPixbuf

from pychess.ic.FICSObjects import FICSPlayer, get_player_tooltip_text
from pychess.ic import TYPE_BLITZ, TYPE_LIGHTNING, TYPE_STANDARD, IC_STATUS_PLAYING
from pychess.System.Log import log
from pychess.System import conf, uistuff
from pychess.System.prefix import addDataPrefix
from pychess.perspectives.fics.ParrentListSection import ParrentListSection, \
    SEPARATOR, FOLLOW, FINGER, ARCHIVED, OBSERVE, CHAT, CHALLENGE


__title__ = _("Player List")

__icon__ = addDataPrefix("glade/panel_players.svg")

__desc__ = _("List of players")


class Sidepanel(ParrentListSection):

    def load(self, widgets, connection, lounge):
        self.widgets = widgets
        self.connection = connection
        lounge.players_tab = self
        self.lounge = lounge

        __widget__ = lounge.players_list

        self.players = {}
        self.columns = {TYPE_BLITZ: 3, TYPE_STANDARD: 4, TYPE_LIGHTNING: 5}

        self.tv = widgets["playertreeview"]
        self.store = Gtk.ListStore(FICSPlayer, GdkPixbuf.Pixbuf, str, int, int,
                                   int, str, str)
        self.player_filter = self.store.filter_new()
        self.player_filter.set_visible_func(self.player_filter_func)

        self.filter_toggles = {}
        self.filter_buttons = ("registered_toggle", "guest_toggle", "computer_toggle", "titled_toggle")
        for widget in self.filter_buttons:
            uistuff.keep(self.widgets[widget], widget)
            self.widgets[widget].connect("toggled", self.on_filter_button_toggled)
            initial = conf.get(widget)
            self.filter_toggles[widget] = initial
            self.widgets[widget].set_active(initial)

        self.model = self.player_filter.sort_new_with_model()
        self.tv.set_model(self.model)

        self.addColumns(self.tv,
                        "FICSPlayer",
                        "",
                        _("Name"),
                        _("Blitz"),
                        _("Standard"),
                        _("Lightning"),
                        _("Status"),
                        "tooltip",
                        hide=[0, 7],
                        pix=[1])
        self.tv.set_tooltip_column(7, )
        self.tv.get_model().set_sort_func(0, self.pixCompareFunction, 1)
        try:
            self.tv.set_search_position_func(self.lowLeftSearchPosFunc, None)
        except AttributeError:
            # Unknow signal name is raised by gtk < 2.10
            pass

        connection.players.connect("FICSPlayerEntered", self.onPlayerAdded)
        connection.players.connect("FICSPlayerExited", self.onPlayerRemoved)

        widgets["private_chat_button"].connect("clicked", self.on_chat)
        widgets["private_chat_button"].set_sensitive(False)
        widgets["observe_button"].connect("clicked", self.on_observe)
        widgets["observe_button"].set_sensitive(False)

        self.tv.get_selection().connect_after("changed", self.onSelectionChanged)
        self.onSelectionChanged(None)

        self.tv.connect('button-press-event', self.button_press_event)
        self.createLocalMenu((CHALLENGE, CHAT, OBSERVE, FOLLOW, SEPARATOR, FINGER, ARCHIVED))

        return __widget__

    def player_filter_func(self, model, iter, data):
        player = model[iter][0]
        is_titled = player.isTitled()
        is_computer = player.isComputer()
        is_registered = (not is_titled) and (not is_computer) and (not player.isGuest())
        is_guest = (not is_titled) and (not is_computer) and (player.isGuest())
        return (
            self.filter_toggles["computer_toggle"] and is_computer) or (
            self.filter_toggles["registered_toggle"] and is_registered) or (
            self.filter_toggles["guest_toggle"] and is_guest) or (
            self.filter_toggles["titled_toggle"] and is_titled)

    def on_filter_button_toggled(self, widget):
        for button in self.filter_buttons:
            self.filter_toggles[button] = self.widgets[button].get_active()
        self.player_filter.refilter()

    def onPlayerAdded(self, players, new_players):
        # Let the hard work to be done in the helper connection thread
        np = {}
        for player in new_players:
            np[player] = (player, player.getIcon(),
                          player.name + player.display_titles(), player.blitz,
                          player.standard, player.lightning,
                          player.display_status,
                          get_player_tooltip_text(player))

        def do_onPlayerAdded(players, new_players, np):
            for player in new_players:
                # log.debug("%s" % player,
                # extra={"task": (self.connection.username,
                # "PTS.onPlayerAdded")})
                if player in self.players:
                    # log.warning("%s already in self" % player,
                    # extra={"task": (self.connection.username,
                    # "PTS.onPlayerAdded")})
                    continue

                # player can leave before we finish processing "who IbslwBzSLx"
                if player not in np:
                    continue

                self.players[player] = {}

                self.players[player]["ti"] = self.store.append(np[player])
                self.players[player]["status"] = player.connect(
                    "notify::status", self.status_changed)
                self.players[player]["game"] = player.connect(
                    "notify::game", self.status_changed)
                self.players[player]["titles"] = player.connect(
                    "notify::titles", self.titles_changed)
                if player.game:
                    self.players[player]["private"] = player.game.connect(
                        "notify::private", self.private_changed, player)
                self.players[player]["ratings"] = player.connect(
                    "ratings_changed", self.elo_changed, player)

            count = len(self.players)
            self.widgets["playersOnlineLabel"].set_text(_("Players: %d") %
                                                        count)

            return False

        GLib.idle_add(do_onPlayerAdded,
                      players,
                      new_players,
                      np,
                      priority=GLib.PRIORITY_LOW)

    def onPlayerRemoved(self, players, player):
        def do_onPlayerRemoved(players, player):
            log.debug("%s" % player,
                      extra={"task": (self.connection.username,
                                      "PTS.onPlayerRemoved")})
            if player not in self.players:
                return
            if self.store.iter_is_valid(self.players[player]["ti"]):
                self.store.remove(self.players[player]["ti"])
            for key in ("status", "game", "titles"):
                if player.handler_is_connected(self.players[player][key]):
                    player.disconnect(self.players[player][key])
            if player.game and "private" in self.players[player] and \
                    player.game.handler_is_connected(self.players[player]["private"]):
                player.game.disconnect(self.players[player]["private"])
            if player.handler_is_connected(self.players[player]["ratings"]):
                player.disconnect(self.players[player]["ratings"])
            del self.players[player]
            count = len(self.players)
            self.widgets["playersOnlineLabel"].set_text(_("Players: %d") % count)

        GLib.idle_add(do_onPlayerRemoved, players, player, priority=GLib.PRIORITY_LOW)

    def status_changed(self, player, prop):
        log.debug(
            "%s" % player,
            extra={"task": (self.connection.username, "PTS.status_changed")})
        if player not in self.players:
            return

        try:
            self.store.set(self.players[player]["ti"], 6,
                           player.display_status)
            self.store.set(self.players[player]["ti"], 7,
                           get_player_tooltip_text(player))
        except KeyError:
            pass

        if player.status == IC_STATUS_PLAYING and player.game and \
                "private" not in self.players[player]:
            self.players[player]["private"] = player.game.connect(
                "notify::private", self.private_changed, player)
        elif player.status != IC_STATUS_PLAYING and \
                "private" in self.players[player]:
            game = player.game
            if game and game.handler_is_connected(self.players[player][
                    "private"]):
                game.disconnect(self.players[player]["private"])
            del self.players[player]["private"]

        if player == self.getSelectedPlayer():
            self.onSelectionChanged(None)

        return False

    def titles_changed(self, player, prop):
        log.debug(
            "%s" % player,
            extra={"task": (self.connection.username, "PTS.titles_changed")})
        try:
            self.store.set(self.players[player]["ti"], 1, player.getIcon())
            self.store.set(self.players[player]["ti"], 2,
                           player.name + player.display_titles())
            self.store.set(self.players[player]["ti"], 7,
                           get_player_tooltip_text(player))
        except KeyError:
            pass

        return False

    def private_changed(self, game, prop, player):
        log.debug(
            "%s" % player,
            extra={"task": (self.connection.username, "PTS.private_changed")})
        self.status_changed(player, prop)
        self.onSelectionChanged(self.tv.get_selection())
        return False

    def elo_changed(self, rating, prop, rating_type, player):
        log.debug(
            "%s %s" % (rating, player),
            extra={"task": (self.connection.username, "PTS_changed")})

        try:
            self.store.set(self.players[player]["ti"], 1, player.getIcon())
            self.store.set(self.players[player]["ti"], 7,
                           get_player_tooltip_text(player))
            self.store.set(self.players[player]["ti"],
                           self.columns[rating_type], rating)
        except KeyError:
            pass

        return False

    def getSelectedPlayer(self):
        model, sel_iter = self.widgets["playertreeview"].get_selection(
        ).get_selected()
        if sel_iter:
            return model.get_value(sel_iter, 0)

    def onSelectionChanged(self, selection):
        player = self.getSelectedPlayer()
        user_name = self.connection.getUsername()
        self.widgets["private_chat_button"].set_sensitive(player is not None)
        self.widgets["observe_button"].set_sensitive(
            player is not None and
            player.isObservable() and
            (player.game is None or
             user_name not in (player.game.wplayer.name, player.game.bplayer.name)))
        self.widgets["challengeButton"].set_sensitive(
            player is not None and
            player.isAvailableForGame() and
            player.name != user_name)

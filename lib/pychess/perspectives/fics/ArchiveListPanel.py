# -*- coding: UTF-8 -*-

from io import StringIO

from gi.repository import Gtk

from pychess.compat import create_task
from pychess.ic.FICSObjects import FICSGame, FICSAdjournedGame, make_sensitive_if_available
from pychess.ic import get_infobarmessage_content
from pychess.ic.ICGameModel import ICGameModel

from pychess.Utils.const import WHITE, BLACK, REMOTE, reprResult
from pychess.Utils.TimeModel import TimeModel
from pychess.Players.ICPlayer import ICPlayer
from pychess.Savers import pgn
from pychess.System.Log import log
from pychess.System.prefix import addDataPrefix
from pychess.perspectives import perspective_manager
from pychess.perspectives.fics.ParrentListSection import ParrentListSection, cmp, \
    SEPARATOR, FOLLOW, CHAT, CHALLENGE, FINGER, ARCHIVED
from pychess.widgets.InfoBar import InfoBarMessage, InfoBarMessageButton


__title__ = _("Archived")

__icon__ = addDataPrefix("glade/panel_games.svg")

__desc__ = _("Adjourned, history and journal games list")


class Sidepanel(ParrentListSection):

    def load(self, widgets, connection, lounge):
        self.connection = connection
        self.widgets = widgets
        self.lounge = lounge
        self.infobar = lounge.infobar

        __widget__ = lounge.archive_list

        self.games = {}
        self.messages = {}
        self.tv = widgets["adjournedtreeview"]
        self.store = Gtk.ListStore(FICSGame, str, str, str, str, str, str, str,
                                   str, str, int)
        self.model = Gtk.TreeModelSort(model=self.store)
        self.tv.set_model(self.model)
        self.addColumns(self.tv,
                        "FICSGame",
                        _("White"),
                        "",
                        "",
                        _("Black"),
                        "",
                        _("Rated"),
                        _("Clock"),
                        _("Type"),
                        _("Date/Time"),
                        "sortable_time",
                        hide=[0, 10])
        self.selection = self.tv.get_selection()
        self.selection.connect("changed", self.onSelectionChanged)
        self.onSelectionChanged(self.selection)
        self.tv.get_model().set_sort_func(5, self.compareFunction, 7)

        self.connection.adm.connect("adjournedGameAdded",
                                    self.onAdjournedGameAdded)
        self.connection.games.connect("FICSAdjournedGameRemoved",
                                      self.onAdjournedGameRemoved)
        self.connection.adm.connect("historyGameAdded",
                                    self.onHistoryGameAdded)
        self.connection.games.connect("FICSHistoryGameRemoved",
                                      self.onHistoryGameRemoved)
        self.connection.adm.connect("journalGameAdded",
                                    self.onJournalGameAdded)
        self.connection.games.connect("FICSJournalGameRemoved",
                                      self.onJournalGameRemoved)

        widgets["resignButton"].connect("clicked", self.onResignButtonClicked)
        widgets["abortButton"].connect("clicked", self.onAbortButtonClicked)
        widgets["drawButton"].connect("clicked", self.onDrawButtonClicked)
        widgets["resumeButton"].connect("clicked", self.onResumeButtonClicked)
        widgets["previewButton"].connect("clicked",
                                         self.onPreviewButtonClicked)
        widgets["examineButton"].connect("clicked",
                                         self.onExamineButtonClicked)
        widgets["mygamesButton"].connect("clicked",
                                         self.onMygamesButtonClicked)
        self.tv.connect("row-activated",
                        lambda *args: self.onPreviewButtonClicked(None))
        self.connection.bm.connect("archiveGamePreview", self.onGamePreview)
        self.connection.bm.connect("playGameCreated", self.onPlayGameCreated)

        self.tv.connect('button-press-event', self.button_press_event)
        self.createLocalMenu((CHALLENGE, CHAT, FOLLOW, SEPARATOR, FINGER, ARCHIVED))

        return __widget__

    def getSelectedPlayer(self):
        model = self.tv.get_model()
        path, col = self.tv.get_cursor()
        col_index = self.tv.get_columns().index(col)
        game = model.get_value(model.get_iter(path), 0)
        return game.bplayer if col_index >= 3 else game.wplayer

    def onSelectionChanged(self, selection):
        model, treeiter = selection.get_selected()
        a_row_is_selected = False
        if treeiter is not None:
            a_row_is_selected = True
            game = model.get_value(treeiter, 0)
            if isinstance(game, FICSAdjournedGame) and \
                    self.connection.stored_owner == self.connection.username:
                make_sensitive_if_available(self.widgets["resumeButton"],
                                            game.opponent)
                for button in ("resignButton", "abortButton", "drawButton"):
                    self.widgets[button].set_sensitive(True)
            else:
                for button in ("resignButton", "abortButton", "drawButton",
                               "resumeButton"):
                    self.widgets[button].set_sensitive(False)
        else:
            self.widgets["resumeButton"].set_sensitive(False)
            self.widgets["resumeButton"].set_tooltip_text("")
            for button in ("resignButton", "abortButton", "drawButton"):
                self.widgets[button].set_sensitive(False)
        self.widgets["previewButton"].set_sensitive(a_row_is_selected)
        self.widgets["examineButton"].set_sensitive(a_row_is_selected)

    def onPlayGameCreated(self, bm, board):
        for message in self.messages.values():
            message.dismiss()
        self.messages = {}
        return False

    def _infobar_adjourned_message(self, game, player):
        if player not in self.messages:
            text = _(" with whom you have an adjourned <b>%(timecontrol)s</b> " +
                     "<b>%(gametype)s</b> game is online.") % \
                {"timecontrol": game.display_timecontrol,
                 "gametype": game.game_type.display_text}
            content = get_infobarmessage_content(player,
                                                 text,
                                                 gametype=game.game_type)

            def callback(infobar, response, message):
                log.debug(
                    "%s" % player,
                    extra={"task": (self.connection.username,
                                    "_infobar_adjourned_message.callback")})
                if response == Gtk.ResponseType.ACCEPT:
                    self.connection.client.run_command("match %s" %
                                                       player.name)
                elif response == Gtk.ResponseType.HELP:
                    self.connection.adm.queryMoves(game)
                else:
                    try:
                        self.messages[player].dismiss()
                        del self.messages[player]
                    except KeyError:
                        pass
                return False

            message = InfoBarMessage(Gtk.MessageType.QUESTION, content,
                                     callback)
            message.add_button(InfoBarMessageButton(
                _("Request Continuation"), Gtk.ResponseType.ACCEPT))
            message.add_button(InfoBarMessageButton(
                _("Examine Adjourned Game"), Gtk.ResponseType.HELP))
            message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                    Gtk.ResponseType.CANCEL))
            make_sensitive_if_available(message.buttons[0], player)
            self.messages[player] = message
            self.infobar.push_message(message)

    def compareFunction(self, treemodel, iter0, iter1, column):
        (minute0, minute1) = (treemodel.get_value(iter0, 10),
                              treemodel.get_value(iter1, 10))
        return cmp(minute0, minute1)

    def online_changed(self, player, prop, game):
        log.debug("AdjournedTabSection.online_changed: %s %s" %
                  (repr(player), repr(game)))
        partner = game.bplayer if game.wplayer.name == player.name else game.wplayer
        result = "▷" if partner.name == self.connection.username and game.opponent.online else "*"
        try:
            self.store.set(self.games[game]["ti"], 3, result)
        except KeyError:
            pass

        if self.connection.stored_owner == self.connection.username and \
                player.online and player.adjournment:
            self._infobar_adjourned_message(game, player)
        elif not player.online and player in self.messages:
            self.messages[player].dismiss()
            # calling message.dismiss() might cause it to be removed from
            # self.messages in another callback, so we re-check
            if player in self.messages:
                del self.messages[player]

        return False

    def status_changed(self, player, prop, game):
        log.debug("AdjournedTabSection.status_changed: %s %s" %
                  (repr(player), repr(game)))
        try:
            message = self.messages[player]
        except KeyError:
            pass
        else:
            make_sensitive_if_available(message.buttons[0], player)

        self.onSelectionChanged(self.selection)
        return False

    def onAdjournedGameAdded(self, adm, game):
        if game not in self.games:
            partner = game.bplayer if game.wplayer.name == game.opponent.name else game.wplayer
            result = "▷" if partner.name == self.connection.username and game.opponent.online else "*"
            ti = self.store.append(
                [game, game.wplayer.name, game.wrating, result,
                 game.bplayer.name, game.brating, game.display_rated,
                 game.display_timecontrol, game.game_type.display_text,
                 game.display_time, game.sortable_time])
            self.games[game] = {}
            self.games[game]["ti"] = ti
            self.games[game]["online_cid"] = game.opponent.connect(
                "notify::online", self.online_changed, game)
            self.games[game]["status_cid"] = game.opponent.connect(
                "notify::status", self.status_changed, game)

        if self.connection.stored_owner == self.connection.username and \
                game.opponent.online:
            self._infobar_adjourned_message(game, game.opponent)

        return False

    def onHistoryGameAdded(self, adm, game):
        if game not in self.games:
            ti = self.store.append(
                [game, game.wplayer.name, game.wrating, reprResult[
                    game.result], game.bplayer.name, game.brating,
                 game.display_rated, game.display_timecontrol,
                 game.game_type.display_text, game.display_time,
                 game.sortable_time])
            self.games[game] = {}
            self.games[game]["ti"] = ti

        return False

    def onJournalGameAdded(self, adm, game):
        if game not in self.games:
            ti = self.store.append(
                [game, game.wplayer.name, game.wrating, reprResult[
                    game.result], game.bplayer.name, game.brating,
                 game.display_rated, game.display_timecontrol,
                 game.game_type.display_text, game.display_time,
                 game.sortable_time])
            self.games[game] = {}
            self.games[game]["ti"] = ti

        return False

    def onAdjournedGameRemoved(self, adm, game):
        if game in self.games:
            if self.store.iter_is_valid(self.games[game]["ti"]):
                self.store.remove(self.games[game]["ti"])
            if game.opponent.handler_is_connected(self.games[game][
                    "online_cid"]):
                game.opponent.disconnect(self.games[game]["online_cid"])
            if game.opponent.handler_is_connected(self.games[game][
                    "status_cid"]):
                game.opponent.disconnect(self.games[game]["status_cid"])
            if game.opponent in self.messages:
                self.messages[game.opponent].dismiss()
                if game.opponent in self.messages:
                    del self.messages[game.opponent]
            del self.games[game]

        return False

    def onHistoryGameRemoved(self, adm, game):
        if game in self.games:
            if self.store.iter_is_valid(self.games[game]["ti"]):
                self.store.remove(self.games[game]["ti"])
            del self.games[game]

        return False

    def onJournalGameRemoved(self, adm, game):
        if game in self.games:
            if self.store.iter_is_valid(self.games[game]["ti"]):
                self.store.remove(self.games[game]["ti"])
            del self.games[game]

        return False

    def onResignButtonClicked(self, button):
        model, sel_iter = self.tv.get_selection().get_selected()
        if sel_iter is None:
            return
        game = model.get_value(sel_iter, 0)
        self.connection.adm.resign(game)

    def onDrawButtonClicked(self, button):
        model, sel_iter = self.tv.get_selection().get_selected()
        if sel_iter is None:
            return
        game = model.get_value(sel_iter, 0)
        self.connection.adm.draw(game)

    def onAbortButtonClicked(self, button):
        model, sel_iter = self.tv.get_selection().get_selected()
        if sel_iter is None:
            return
        game = model.get_value(sel_iter, 0)
        self.connection.adm.abort(game)

    def onResumeButtonClicked(self, button):
        model, sel_iter = self.tv.get_selection().get_selected()
        if sel_iter is None:
            return
        game = model.get_value(sel_iter, 0)
        self.connection.adm.resume(game)

    def onPreviewButtonClicked(self, button):
        model, sel_iter = self.tv.get_selection().get_selected()
        if sel_iter is None:
            return
        game = model.get_value(sel_iter, 0)
        self.connection.adm.queryMoves(game)

    def onExamineButtonClicked(self, button):
        model, sel_iter = self.tv.get_selection().get_selected()
        if sel_iter is None:
            return
        game = model.get_value(sel_iter, 0)
        if self.connection.examined_game is None:
            self.connection.adm.examine(game)
        else:
            self.lounge.nonoWhileExamine(None)

    def onMygamesButtonClicked(self, button):
        self.connection.adm.queryAdjournments()
        self.connection.adm.queryHistory()
        self.connection.adm.queryJournal()

    def onGamePreview(self, adm, ficsgame):
        log.debug("Archived panel onGamePreview: %s" % ficsgame)

        timemodel = TimeModel(ficsgame.minutes * 60, ficsgame.inc)

        gamemodel = ICGameModel(self.connection, ficsgame, timemodel)

        # The players need to start listening for moves IN this method if they
        # want to be noticed of all moves the FICS server sends us from now on.
        # Hence the lazy loading is skipped.
        wplayer, bplayer = ficsgame.wplayer, ficsgame.bplayer
        player0tup = (REMOTE, ICPlayer, (
            gamemodel, wplayer.name, -1, WHITE,
            wplayer.long_name(), wplayer.getRatingByGameType(ficsgame.game_type)),
            wplayer.long_name())
        player1tup = (REMOTE, ICPlayer, (
            gamemodel, bplayer.name, -1, BLACK,
            bplayer.long_name(), bplayer.getRatingByGameType(ficsgame.game_type)),
            bplayer.long_name())

        perspective = perspective_manager.get_perspective("games")
        create_task(perspective.generalStart(gamemodel, player0tup, player1tup, (
            StringIO(ficsgame.board.pgn), pgn, 0, -1)))
        gamemodel.connect("game_started", self.on_game_start, ficsgame)

    def on_game_start(self, gamemodel, ficsgame):
        gamemodel.end(ficsgame.result, ficsgame.reason)

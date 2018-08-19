# -*- coding: utf-8 -*-

import os
from io import StringIO

from gi.repository import GLib, Gtk, GObject

from pychess.compat import create_task
from pychess.ic import IC_POS_EXAMINATING, IC_POS_OBSERVING_EXAMINATION, \
    get_infobarmessage_content, get_infobarmessage_content2, TITLES
from pychess.ic.ICGameModel import ICGameModel
from pychess.perspectives.fics.FicsHome import UserInfoSection
from pychess.perspectives.fics.SeekChallenge import SeekChallengeSection
from pychess.System import conf, uistuff
from pychess.System.prefix import addUserConfigPrefix
from pychess.System.Log import log
from pychess.widgets import new_notebook
from pychess.widgets.InfoBar import InfoBarMessage, InfoBarNotebook, InfoBarMessageButton
from pychess.widgets.pydock.PyDockTop import PyDockTop
from pychess.widgets.pydock import SOUTH, WEST, CENTER

from pychess.Utils.const import LOCAL, WHITE, BLACK, REMOTE
from pychess.Utils.TimeModel import TimeModel
from pychess.Players.ICPlayer import ICPlayer
from pychess.Players.Human import Human
from pychess.Savers import pgn, fen
from pychess.perspectives import Perspective, perspective_manager, panel_name


class PlayerNotificationMessage(InfoBarMessage):

    def __init__(self, message_type, content, callback, player, text):
        InfoBarMessage.__init__(self, message_type, content, callback)
        self.player = player
        self.text = text


class FICS(GObject.GObject, Perspective):
    __gsignals__ = {
        'logout': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'autoLogout': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        log.debug("FICS.__init__: starting")
        GObject.GObject.__init__(self)
        Perspective.__init__(self, "fics", _("ICS"))
        self.dockLocation = addUserConfigPrefix("pydock-fics.xml")
        self.first_run = True

    def create_toolbuttons(self):
        def on_logoff_clicked(button):
            self.emit("logout")
            self.close()

        self.logoff_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_DISCONNECT)
        self.logoff_button.set_tooltip_text(_("Log Off"))
        self.logoff_button.set_label("logoff")
        self.logoff_button.connect("clicked", on_logoff_clicked)

        def on_minute_1_clicked(button):
            self.connection.client.run_command("1-minute")

        def on_minute_3_clicked(button):
            self.connection.client.run_command("3-minute")

        def on_minute_5_clicked(button):
            self.connection.client.run_command("5-minute")

        def on_minute_15_clicked(button):
            self.connection.client.run_command("15-minute")

        def on_minute_25_clicked(button):
            self.connection.client.run_command("25-minute")

        def on_chess960_clicked(button):
            self.connection.client.run_command("chess960")

        self.minute_1_button = Gtk.ToggleToolButton()
        self.minute_1_button.set_label("1")
        self.minute_1_button.set_tooltip_text(_("New game from 1-minute playing pool"))
        self.minute_1_button.connect("clicked", on_minute_1_clicked)

        self.minute_3_button = Gtk.ToggleToolButton()
        self.minute_3_button.set_label("3")
        self.minute_3_button.set_tooltip_text(_("New game from 3-minute playing pool"))
        self.minute_3_button.connect("clicked", on_minute_3_clicked)

        self.minute_5_button = Gtk.ToggleToolButton()
        self.minute_5_button.set_label("5")
        self.minute_5_button.set_tooltip_text(_("New game from 5-minute playing pool"))
        self.minute_5_button.connect("clicked", on_minute_5_clicked)

        self.minute_15_button = Gtk.ToggleToolButton()
        self.minute_15_button.set_label("15")
        self.minute_15_button.set_tooltip_text(_("New game from 15-minute playing pool"))
        self.minute_15_button.connect("clicked", on_minute_15_clicked)

        self.minute_25_button = Gtk.ToggleToolButton()
        self.minute_25_button.set_label("25")
        self.minute_25_button.set_tooltip_text(_("New game from 25-minute playing pool"))
        self.minute_25_button.connect("clicked", on_minute_25_clicked)

        self.chess960_button = Gtk.ToggleToolButton()
        self.chess960_button.set_label("960")
        self.chess960_button.set_tooltip_text(_("New game from Chess960 playing pool"))
        self.chess960_button.connect("clicked", on_chess960_clicked)

    def init_layout(self):
        perspective_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        perspective_manager.set_perspective_widget("fics", perspective_widget)

        self.infobar = InfoBarNotebook("fics_lounge_infobar")
        self.infobar.hide()
        perspective_widget.pack_start(self.infobar, False, False, 0)

        self.dock = PyDockTop("fics", self)
        align = Gtk.Alignment()
        align.show()
        align.add(self.dock)
        self.dock.show()
        perspective_widget.pack_start(align, True, True, 0)

        self.notebooks = {"ficshome": new_notebook()}
        self.main_notebook = self.notebooks["ficshome"]
        for panel in self.sidePanels:
            self.notebooks[panel_name(panel.__name__)] = new_notebook(panel_name(panel.__name__))

        self.docks["ficshome"] = (Gtk.Label(label="ficshome"), self.notebooks["ficshome"], None)
        for panel in self.sidePanels:
            self.docks[panel_name(panel.__name__)][1] = self.notebooks[panel_name(panel.__name__)]

        self.load_from_xml()

        # Default layout of side panels
        first_time_layout = False
        if not os.path.isfile(self.dockLocation):
            first_time_layout = True
            leaf = self.dock.dock(self.docks["ficshome"][1], CENTER, self.docks["ficshome"][0], "ficshome")
            leaf.setDockable(False)

            console_leaf = leaf.dock(self.docks["ConsolePanel"][1], SOUTH, self.docks["ConsolePanel"][0], "ConsolePanel")
            console_leaf.dock(self.docks["NewsPanel"][1], CENTER, self.docks["NewsPanel"][0], "NewsPanel")

            seek_leaf = leaf.dock(self.docks["SeekListPanel"][1], WEST, self.docks["SeekListPanel"][0], "SeekListPanel")
            seek_leaf.dock(self.docks["SeekGraphPanel"][1], CENTER, self.docks["SeekGraphPanel"][0], "SeekGraphPanel")
            seek_leaf.dock(self.docks["PlayerListPanel"][1], CENTER, self.docks["PlayerListPanel"][0], "PlayerListPanel")
            seek_leaf.dock(self.docks["GameListPanel"][1], CENTER, self.docks["GameListPanel"][0], "GameListPanel")
            seek_leaf.dock(self.docks["ArchiveListPanel"][1], CENTER, self.docks["ArchiveListPanel"][0], "ArchiveListPanel")

            leaf = leaf.dock(self.docks["ChatPanel"][1], SOUTH, self.docks["ChatPanel"][0], "ChatPanel")
            # leaf.dock(self.docks["LecturesPanel"][1], CENTER, self.docks["LecturesPanel"][0], "LecturesPanel")

        def unrealize(dock):
            dock.saveToXML(self.dockLocation)
            dock._del()

        self.dock.connect("unrealize", unrealize)

        self.dock.show_all()
        perspective_widget.show_all()

        perspective_manager.set_perspective_menuitems("fics", self.menuitems, default=first_time_layout)

        log.debug("FICS.__init__: finished")

    def open_lounge(self, connection, helperconn, host):
        if self.first_run:
            self.init_layout()

        self.connection = connection
        self.helperconn = helperconn
        self.host = host

        self.finger_sent = False
        self.messages = []
        self.players = []
        self.game_cids = {}

        self.widgets = uistuff.GladeWidgets("fics_lounge.glade")
        self.widgets["fics_lounge"].hide()

        fics_home = self.widgets["fics_home"]
        self.widgets["fics_lounge_content_hbox"].remove(fics_home)

        self.archive_list = self.widgets["archiveListContent"]
        self.widgets["fics_panels_notebook"].remove(self.archive_list)

        self.games_list = self.widgets["gamesListContent"]
        self.widgets["fics_panels_notebook"].remove(self.games_list)

        self.news_list = self.widgets["news"]
        self.widgets["fics_home"].remove(self.news_list)

        self.players_list = self.widgets["playersListContent"]
        self.widgets["fics_panels_notebook"].remove(self.players_list)

        self.seek_graph = self.widgets["seekGraphContent"]
        self.widgets["fics_panels_notebook"].remove(self.seek_graph)

        self.seek_list = self.widgets["seekListContent"]
        self.widgets["fics_panels_notebook"].remove(self.seek_list)

        self.seek_challenge = SeekChallengeSection(self)

        def on_autoLogout(alm):
            self.emit("autoLogout")
            self.close()

        self.connection.alm.connect("logOut", on_autoLogout)
        self.connection.connect("disconnected", lambda connection: self.close())
        self.connection.connect("error", self.on_connection_error)
        if self.connection.isRegistred():
            numtimes = conf.get("numberOfTimesLoggedInAsRegisteredUser") + 1
            conf.set("numberOfTimesLoggedInAsRegisteredUser", numtimes)
        self.connection.em.connect("onCommandNotFound", lambda em, cmd: log.error(
            "Fics answered '%s': Command not found" % cmd))
        self.connection.bm.connect("playGameCreated", self.onPlayGameCreated)
        self.connection.bm.connect("obsGameCreated", self.onObserveGameCreated)
        self.connection.bm.connect("exGameCreated", self.onObserveGameCreated)
        self.connection.fm.connect("fingeringFinished", self.onFinger)
        # the rest of these relay server messages to the lounge infobar
        self.connection.bm.connect("tooManySeeks", self.tooManySeeks)
        self.connection.bm.connect("nonoWhileExamine", self.nonoWhileExamine)
        self.connection.bm.connect("matchDeclined", self.matchDeclined)
        self.connection.bm.connect("player_on_censor", self.player_on_censor)
        self.connection.bm.connect("player_on_noplay", self.player_on_noplay)
        self.connection.bm.connect("req_not_fit_formula", self.req_not_fit_formula)
        self.connection.glm.connect("seek-updated", self.on_seek_updated)
        self.connection.glm.connect("our-seeks-removed", self.our_seeks_removed)
        self.connection.cm.connect("arrivalNotification", self.onArrivalNotification)
        self.connection.cm.connect("departedNotification", self.onDepartedNotification)

        def get_top_games():
            if perspective_manager.current_perspective == self:
                self.connection.client.run_command("games *19")
            return True

        if self.connection.ICC:
            self.event_id = GLib.timeout_add_seconds(5, get_top_games)

        for user in self.connection.notify_users:
            user = self.connection.players.get(user)
            self.user_from_notify_list_is_present(user)

        self.userinfo = UserInfoSection(self.widgets, self.connection, self.host, self)
        if not self.first_run:
            self.notebooks["ficshome"].remove_page(-1)
        self.notebooks["ficshome"].append_page(fics_home)

        self.panels = [panel.Sidepanel().load(self.widgets, self.connection, self) for panel in self.sidePanels]

        for panel, instance in zip(self.sidePanels, self.panels):
            if not self.first_run:
                self.notebooks[panel_name(panel.__name__)].remove_page(-1)
            self.notebooks[panel_name(panel.__name__)].append_page(instance)
            instance.show()

        tool_buttons = [self.logoff_button, ]
        self.quick_seek_buttons = []
        if self.connection.ICC:
            self.quick_seek_buttons = [self.minute_1_button, self.minute_3_button, self.minute_5_button,
                                       self.minute_15_button, self.minute_25_button, self.chess960_button]
            tool_buttons += self.quick_seek_buttons
        perspective_manager.set_perspective_toolbuttons("fics", tool_buttons)

        if self.first_run:
            self.first_run = False

        # After all panel is set up we can push initial messages out
        self.connection.com.onConsoleMessage("", self.connection.ini_messages)

    def show(self):
        perspective_manager.activate_perspective("fics")

    def present(self):
        perspective_manager.activate_perspective("fics")

    def on_connection_error(self, connection, error):
        log.warning("FICS.on_connection_error: %s" % repr(error))
        self.close()

    def close(self):
        try:
            self.widgets = None
        except TypeError:
            pass
        except AttributeError:
            pass
        perspective_manager.disable_perspective("fics")

    def onPlayGameCreated(self, bm, ficsgame):
        log.debug("FICS.onPlayGameCreated: %s" % ficsgame)

        for message in self.messages:
            message.dismiss()
        del self.messages[:]

        if self.connection.ICC:
            for button in self.quick_seek_buttons:
                button.set_active(False)

        timemodel = TimeModel(ficsgame.minutes * 60, ficsgame.inc)

        gamemodel = ICGameModel(self.connection, ficsgame, timemodel)
        gamemodel.connect("game_started", self.onGameModelStarted, ficsgame)

        wplayer, bplayer = ficsgame.wplayer, ficsgame.bplayer

        # We start
        if wplayer.name.lower() == self.connection.getUsername().lower():
            player0tup = (LOCAL, Human,
                          (WHITE, wplayer.long_name(), wplayer.name,
                           wplayer.getRatingForCurrentGame()),
                          wplayer.long_name())
            player1tup = (REMOTE, ICPlayer, (
                gamemodel, bplayer.name, ficsgame.gameno, BLACK,
                bplayer.long_name(), bplayer.getRatingForCurrentGame()),
                bplayer.long_name())

        # She starts
        else:
            player1tup = (LOCAL, Human,
                          (BLACK, bplayer.long_name(), bplayer.name,
                           bplayer.getRatingForCurrentGame()),
                          bplayer.long_name())
            player0tup = (REMOTE, ICPlayer, (
                gamemodel, wplayer.name, ficsgame.gameno, WHITE,
                wplayer.long_name(), wplayer.getRatingForCurrentGame()),
                wplayer.long_name())

        perspective = perspective_manager.get_perspective("games")
        if not ficsgame.board.fen:
            create_task(perspective.generalStart(gamemodel, player0tup, player1tup))
        else:
            create_task(perspective.generalStart(gamemodel, player0tup, player1tup, (
                StringIO(ficsgame.board.fen), fen, 0, -1)))

    def onGameModelStarted(self, gamemodel, ficsgame):
        self.connection.bm.onGameModelStarted(ficsgame.gameno)

    def onObserveGameCreated(self, bm, ficsgame):
        log.debug("FICS.onObserveGameCreated: %s" % ficsgame)

        timemodel = TimeModel(ficsgame.minutes * 60, ficsgame.inc)

        gamemodel = ICGameModel(self.connection, ficsgame, timemodel)
        gamemodel.connect("game_started", self.onGameModelStarted, ficsgame)

        # The players need to start listening for moves IN this method if they
        # want to be noticed of all moves the FICS server sends us from now on
        wplayer, bplayer = ficsgame.wplayer, ficsgame.bplayer

        player0tup = (REMOTE, ICPlayer, (
            gamemodel, wplayer.name, ficsgame.gameno, WHITE,
            wplayer.long_name(), wplayer.getRatingForCurrentGame()),
            wplayer.long_name())
        player1tup = (REMOTE, ICPlayer, (
            gamemodel, bplayer.name, ficsgame.gameno, BLACK,
            bplayer.long_name(), bplayer.getRatingForCurrentGame()),
            bplayer.long_name())

        perspective = perspective_manager.get_perspective("games")
        create_task(perspective.generalStart(gamemodel, player0tup, player1tup, (
            StringIO(ficsgame.board.pgn), pgn, 0, -1)))

        if ficsgame.relation == IC_POS_OBSERVING_EXAMINATION:
            if 1:  # int(self.connection.lvm.variablesBackup["kibitz"]) == 0:
                self.connection.cm.whisper(_(
                    "You have to set kibitz on to see bot messages here."))
            self.connection.fm.finger(bplayer.name)
            self.connection.fm.finger(wplayer.name)
        elif ficsgame.relation == IC_POS_EXAMINATING:
            gamemodel.examined = True
        if not self.connection.ICC:
            allob = 'allob ' + str(ficsgame.gameno)
            gamemodel.connection.client.run_command(allob)

    def onFinger(self, fm, finger):
        titles = finger.getTitles()
        if titles is not None:
            name = finger.getName()
            player = self.connection.players.get(name)
            for title in titles:
                player.titles.add(TITLES[title])

    def tooManySeeks(self, bm):
        label = Gtk.Label(label=_(
            "You may only have 3 outstanding seeks at the same time. If you want \
            to add a new seek you must clear your currently active seeks. Clear your seeks?"))
        label.set_width_chars(80)
        label.props.xalign = 0
        label.set_line_wrap(True)

        def response_cb(infobar, response, message):
            if response == Gtk.ResponseType.YES:
                self.connection.client.run_command("unseek")
            message.dismiss()
            return False

        message = InfoBarMessage(Gtk.MessageType.QUESTION, label, response_cb)
        message.add_button(InfoBarMessageButton(Gtk.STOCK_YES,
                                                Gtk.ResponseType.YES))
        message.add_button(InfoBarMessageButton(Gtk.STOCK_NO,
                                                Gtk.ResponseType.NO))
        self.messages.append(message)
        self.infobar.push_message(message)

    def nonoWhileExamine(self, bm):
        label = Gtk.Label(_("You can't touch this! You are examining a game."))

        def response_cb(infobar, response, message):
            message.dismiss()
            return False

        message = InfoBarMessage(Gtk.MessageType.INFO, label, response_cb)
        message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                Gtk.ResponseType.CANCEL))
        self.messages.append(message)
        self.infobar.push_message(message)

    def matchDeclined(self, bm, player):
        text = _(" has declined your offer for a match")
        content = get_infobarmessage_content(player, text)

        def response_cb(infobar, response, message):
            message.dismiss()
            return False

        message = InfoBarMessage(Gtk.MessageType.INFO, content, response_cb)
        message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                Gtk.ResponseType.CANCEL))
        self.messages.append(message)
        self.infobar.push_message(message)

    def player_on_censor(self, bm, player):
        text = _(" is censoring you")
        content = get_infobarmessage_content(player, text)

        def response_cb(infobar, response, message):
            message.dismiss()
            return False

        message = InfoBarMessage(Gtk.MessageType.INFO, content, response_cb)
        message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                Gtk.ResponseType.CANCEL))
        self.messages.append(message)
        self.infobar.push_message(message)

    def player_on_noplay(self, bm, player):
        text = _(" noplay listing you")
        content = get_infobarmessage_content(player, text)

        def response_cb(infobar, response, message):
            message.dismiss()
            return False

        message = InfoBarMessage(Gtk.MessageType.INFO, content, response_cb)
        message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                Gtk.ResponseType.CANCEL))
        self.messages.append(message)
        self.infobar.push_message(message)

    def req_not_fit_formula(self, bm, player, formula):
        content = get_infobarmessage_content2(
            player, _(" uses a formula not fitting your match request:"),
            formula)

        def response_cb(infobar, response, message):
            message.dismiss()
            return False

        message = InfoBarMessage(Gtk.MessageType.INFO, content, response_cb)
        message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                Gtk.ResponseType.CANCEL))
        self.messages.append(message)
        self.infobar.push_message(message)

    def on_seek_updated(self, glm, message_text):
        if "manual accept" in message_text:
            message_text.replace("to manual accept", _("to manual accept"))
        elif "automatic accept" in message_text:
            message_text.replace("to automatic accept",
                                 _("to automatic accept"))
        if "rating range now" in message_text:
            message_text.replace("rating range now", _("rating range now"))
        label = Gtk.Label(label=_("Seek updated") + ": " + message_text)

        def response_cb(infobar, response, message):
            message.dismiss()
            return False

        message = InfoBarMessage(Gtk.MessageType.INFO, label, response_cb)
        message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                Gtk.ResponseType.CANCEL))
        self.messages.append(message)
        self.infobar.push_message(message)

    def our_seeks_removed(self, glm):
        label = Gtk.Label(label=_("Your seeks have been removed"))

        def response_cb(infobar, response, message):
            message.dismiss()
            return False

        message = InfoBarMessage(Gtk.MessageType.INFO, label, response_cb)
        message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                Gtk.ResponseType.CANCEL))
        self.messages.append(message)
        self.infobar.push_message(message)

    def _connect_to_player_changes(self, player):
        player.connect("ratings_changed", self._replace_notification_message, player)
        player.connect("notify::titles", self._replace_notification_message, None, player)

    def onArrivalNotification(self, cm, player):
        log.debug("%s" % player,
                  extra={"task": (self.connection.username,
                                  "onArrivalNotification")})
        self._add_notification_message(player, _(" has arrived"), chat=True, replace=True)
        if player not in self.players:
            self.players.append(player)
            self._connect_to_player_changes(player)

    def onDepartedNotification(self, cm, player):
        self._add_notification_message(player, _(" has departed"), replace=True)

    def user_from_notify_list_is_present(self, player):
        self._add_notification_message(player, _(" is present"), chat=True, replace=True)
        if player not in self.players:
            self.players.append(player)
            self._connect_to_player_changes(player)

    def _add_notification_message(self, player, text, chat=False, replace=False):
        if replace:
            for message in self.messages:
                if isinstance(message, PlayerNotificationMessage) and message.player == player:
                    message.dismiss()

        content = get_infobarmessage_content(player, text)

        def response_cb(infobar, response, message):
            if response == 1:
                if player is None:
                    return
                self.chat.openChatWithPlayer(player.name)
            if response == 2:
                if player is None:
                    return
                self.connection.client.run_command("follow %s" % player.name)
            message.dismiss()
            #             self.messages.remove(message)
            return False

        message = PlayerNotificationMessage(Gtk.MessageType.INFO, content,
                                            response_cb, player, text)
        if chat:
            message.add_button(InfoBarMessageButton(_("Chat"), 1))
            message.add_button(InfoBarMessageButton(_("Follow"), 2))
        message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                Gtk.ResponseType.CANCEL))
        self.messages.append(message)
        self.infobar.push_message(message)

    def _replace_notification_message(self, obj, prop, rating_type, player):
        log.debug("%s %s" % (repr(obj), player),
                  extra={"task": (self.connection.username,
                                  "_replace_notification_message")})
        for message in self.messages:
            if isinstance(message, PlayerNotificationMessage) and \
                    message.player == player:
                message.update_content(get_infobarmessage_content(
                    player, message.text))
        return False

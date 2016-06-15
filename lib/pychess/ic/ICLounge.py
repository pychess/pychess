# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import sys
from math import e
from operator import attrgetter
from itertools import groupby

from gi.repository import GLib, Gtk, Gdk, GdkPixbuf, GObject, Pango

from pychess.ic import IC_POS_EXAMINATING, IC_POS_OBSERVING_EXAMINATION, \
    TYPE_BLITZ, get_infobarmessage_content, get_infobarmessage_content2, \
    TYPE_LIGHTNING, GAME_TYPES_BY_RATING_TYPE, TYPE_WILD, WildGameType, \
    TYPE_STANDARD, TITLES, GAME_TYPES, VARIANT_GAME_TYPES, \
    RATING_TYPES, IC_STATUS_PLAYING, \
    VariantGameType, time_control_to_gametype

from pychess.compat import cmp, StringIO
from pychess.System import conf, uistuff
from pychess.System.prefix import addDataPrefix
from pychess.System.ping import Pinger
from pychess.System.Log import log
from pychess.widgets.ionest import game_handler
from pychess.widgets.ChatWindow import ChatWindow
from pychess.widgets.ConsoleWindow import ConsoleWindow
from pychess.widgets.SpotGraph import SpotGraph
from pychess.widgets.ChainVBox import ChainVBox
from pychess.widgets.preferencesDialog import SoundTab
from pychess.widgets.InfoBar import InfoBarMessage, InfoBarNotebook, InfoBarMessageButton

from pychess.Utils.const import LOCAL, WHITE, BLACK, REMOTE, reprResult, RANDOMCHESS, \
    FISCHERRANDOMCHESS, LOSERSCHESS, UNSUPPORTED, VARIANTS_SHUFFLE, VARIANTS_OTHER, \
    VARIANTS_OTHER_NONSTANDARD
from pychess.Utils.IconLoader import load_icon, get_pixbuf
from pychess.Utils.TimeModel import TimeModel
from pychess.Players.ICPlayer import ICPlayer
from pychess.Players.Human import Human
from pychess.Savers import pgn, fen
from pychess.System.idle_add import idle_add
from pychess.Variants import variants

from .FICSObjects import FICSPlayer, FICSSoughtMatch, FICSChallenge, FICSGame, \
    FICSAdjournedGame, get_seek_tooltip_text, get_challenge_tooltip_text, \
    get_rating_range_display_text, get_player_tooltip_text, \
    make_sensitive_if_available
from .ICGameModel import ICGameModel


class PlayerNotificationMessage(InfoBarMessage):

    def __init__(self, message_type, content, callback, player, text):
        InfoBarMessage.__init__(self, message_type, content, callback)
        self.player = player
        self.text = text


class ICLounge(GObject.GObject):
    __gsignals__ = {
        'logout': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'autoLogout': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, connection, helperconn, host):
        log.debug("ICLounge.__init__: starting")
        GObject.GObject.__init__(self)
        self.connection = connection
        self.helperconn = helperconn
        self.host = host
        self.messages = []
        self.players = []
        self.game_cids = {}
        self.widgets = uistuff.GladeWidgets("fics_lounge.glade")
        lounge = self.widgets["fics_lounge"]
        uistuff.keepWindowSize("fics_lounge", lounge)
        lounge.set_title("PyChess - Internet Chess: %s" % connection.ics_name)
        self.infobar = InfoBarNotebook("fics_lounge_infobar")
        self.infobar.hide()
        self.widgets["fics_lounge_infobar_vbox"].pack_start(self.infobar,
                                                            False, False, 0)

        def on_window_delete(window, event):
            self.emit("logout")
            self.close()
            return True

        self.widgets["fics_lounge"].connect("delete-event", on_window_delete)

        def on_logoffButton_clicked(button):
            self.emit("logout")
            self.close()

        self.widgets["logoffButton"].connect("clicked",
                                             on_logoffButton_clicked)

        def on_autoLogout(alm):
            self.emit("autoLogout")
            self.close()

        self.connection.alm.connect("logOut", on_autoLogout)
        self.connection.connect("disconnected",
                                lambda connection: self.close())
        self.connection.connect("error", self.on_connection_error)
        if self.connection.isRegistred():
            numtimes = conf.get("numberOfTimesLoggedInAsRegisteredUser", 0) + 1
            conf.set("numberOfTimesLoggedInAsRegisteredUser", numtimes)
        self.connection.em.connect(
            "onCommandNotFound",
            lambda em, cmd: log.error("Fics answered '%s': Command not found" % cmd))
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
        self.connection.bm.connect("req_not_fit_formula",
                                   self.req_not_fit_formula)
        self.connection.glm.connect("seek-updated", self.on_seek_updated)
        self.connection.glm.connect("our-seeks-removed",
                                    self.our_seeks_removed)
        self.connection.cm.connect("arrivalNotification",
                                   self.onArrivalNotification)
        self.connection.cm.connect("departedNotification",
                                   self.onDepartedNotification)
        for user in self.connection.notify_users:
            user = self.connection.players.get(user)
            self.user_from_notify_list_is_present(user)

        self.userinfo = UserInfoSection(self.widgets, self.connection,
                                        self.host, self)
        self.news = NewsSection(self.widgets, self.connection)
        self.seek_challenge = SeekChallengeSection(self)
        self.seeks_list = SeekTabSection(self.widgets, self.connection, self)
        self.seeks_graph_tab = SeekGraphSection(self.widgets, self.connection,
                                                self)
        self.players_tab = PlayerTabSection(self.widgets, self.connection,
                                            self)
        self.games_tab = GameTabSection(self.widgets, self.connection, self)
        self.adjourned_games_tab = AdjournedTabSection(self.widgets,
                                                       self.connection, self)
        self.sections = (self.userinfo, self.news, self.seeks_list,
                         self.seek_challenge, self.seeks_graph_tab,
                         self.players_tab, self.games_tab,
                         self.adjourned_games_tab)
        self.chat = ChatWindow(self.widgets, self.connection)
        self.console = ConsoleWindow(self.widgets, self.connection)

        self.connection.com.onConsoleMessage("", self.connection.ini_messages)

        self.finger_sent = False
        self.connection.lounge_loaded.set()

        log.debug("ICLounge.__init__: finished")

    def show(self):
        self.widgets["fics_lounge"].show()

    def present(self):
        self.widgets["fics_lounge"].present()

    def on_connection_error(self, connection, error):
        log.warning("ICLounge.on_connection_error: %s" % repr(error))
        self.close()

    @idle_add
    def close(self):
        try:
            self.widgets["fics_lounge"].hide()
            for section in self.sections:
                section._del()
            self.sections = None
            self.widgets = None
            self.chat.dock._del()
            self.chat.window.remove(self.chat.dock)
            self.chat.dock = None
        except TypeError:
            pass
        except AttributeError:
            pass

    @idle_add
    def onPlayGameCreated(self, bm, ficsgame):
        log.debug("ICLounge.onPlayGameCreated: %s" % ficsgame)

        for message in self.messages:
            message.dismiss()
        del self.messages[:]

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

        if not ficsgame.board.fen:
            game_handler.generalStart(gamemodel, player0tup, player1tup)
        else:
            game_handler.generalStart(gamemodel, player0tup, player1tup, (
                StringIO(ficsgame.board.fen), fen, 0, -1))

    def onGameModelStarted(self, gamemodel, ficsgame):
        self.connection.bm.onGameModelStarted(ficsgame.gameno)

    @idle_add
    def onObserveGameCreated(self, bm, ficsgame):
        log.debug("ICLounge.onObserveGameCreated: %s" % ficsgame)

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

        game_handler.generalStart(gamemodel, player0tup, player1tup, (
            StringIO(ficsgame.board.pgn), pgn, 0, -1))

        if ficsgame.relation == IC_POS_OBSERVING_EXAMINATION:
            if 1:  # int(self.connection.lvm.variablesBackup["kibitz"]) == 0:
                self.connection.cm.whisper(_(
                    "You have to set kibitz on to see bot messages here."))
            self.connection.fm.finger(bplayer.name)
            self.connection.fm.finger(wplayer.name)
        elif ficsgame.relation == IC_POS_EXAMINATING:
            gamemodel.examined = True
        allob = 'allob ' + str(ficsgame.gameno)
        gamemodel.connection.client.run_command(allob)

    @idle_add
    def onFinger(self, fm, finger):
        titles = finger.getTitles()
        if titles is not None:
            name = finger.getName()
            player = self.connection.players.get(name)
            for title in titles:
                player.titles.add(TITLES[title])

    @idle_add
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

    @idle_add
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

    @idle_add
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

    @idle_add
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

    @idle_add
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

    @idle_add
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

    @idle_add
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

    @idle_add
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

    @idle_add
    def onArrivalNotification(self, cm, player):
        log.debug("%s" % player,
                  extra={"task": (self.connection.username,
                                  "onArrivalNotification")})
        self._add_notification_message(player, _(" has arrived"), chat=True, replace=True)
        if player not in self.players:
            self.players.append(player)
            self._connect_to_player_changes(player)

    @idle_add
    def onDepartedNotification(self, cm, player):
        self._add_notification_message(player, _(" has departed"), replace=True)

    @idle_add
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
            message.dismiss()
            #             self.messages.remove(message)
            return False

        message = PlayerNotificationMessage(Gtk.MessageType.INFO, content,
                                            response_cb, player, text)
        if chat:
            message.add_button(InfoBarMessageButton(_("Chat"), 1))
        message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                Gtk.ResponseType.CANCEL))
        self.messages.append(message)
        self.infobar.push_message(message)

    @idle_add
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


class Section(object):

    def _del(self):
        pass


class UserInfoSection(Section):

    def __init__(self, widgets, connection, host, lounge):
        self.widgets = widgets
        self.connection = connection
        self.host = host
        self.lounge = lounge
        self.pinger = None
        self.ping_label = None

        self.dock = self.widgets["fingerTableDock"]

        self.connection.fm.connect("fingeringFinished", self.onFinger)
        self.connection.fm.finger(self.connection.getUsername())
        self.connection.bm.connect(
            "curGameEnded",
            lambda *args: self.connection.fm.finger(self.connection.getUsername()))

        self.widgets["usernameLabel"].set_markup("<b>%s</b>" %
                                                 self.connection.getUsername())

    def _del(self):
        if self.pinger is not None:
            self.pinger.stop()

    @idle_add
    def onFinger(self, fm, finger):
        # print(finger.getName(), self.connection.getUsername())
        my_finger = finger.getName().lower() == self.connection.getUsername().lower()
        if my_finger:
            self.widgets["usernameLabel"].set_markup("<b>%s</b>" % finger.getName())
        rows = 1
        if finger.getRatingsLen() > 0:
            rows += finger.getRatingsLen() + 1
        if finger.getEmail():
            rows += 1
        if finger.getCreated():
            rows += 1

        cols = 6 if my_finger else 9
        table = Gtk.Table(cols, rows)
        table.props.column_spacing = 12
        table.props.row_spacing = 4

        def label(value, xalign=0, is_error=False):
            if is_error:
                label = Gtk.Label()
                label.set_markup('<span size="larger" foreground="red">' +
                                 value + "</span>")
            else:
                label = Gtk.Label(label=value)
            label.props.xalign = xalign
            return label

        row = 0

        ELO, DEVIATION, WINS, LOSSES, DRAWS, TOTAL, BESTELO, BESTTIME = range(8)
        if finger.getRatingsLen() > 0:
            if my_finger:
                headers = (_("Rating"), _("Win"), _("Draw"), _("Loss"))
            else:
                headers = (_("Rating"), "RD", _("Win"), _("Draw"), _("Loss"), _("Best"))
            for i, item in enumerate(headers):
                table.attach(label(item, xalign=1), i + 1, i + 2, 0, 1)
            row += 1
            for rating_type, rating in finger.getRatings().items():
                col = 0
                ratinglabel = label(GAME_TYPES_BY_RATING_TYPE[
                                    rating_type].display_text + ":")
                table.attach(ratinglabel, col, col + 1, row, row + 1)
                col += 1
                if rating_type is TYPE_WILD:
                    ratinglabel.set_tooltip_text(_(
                        "On FICS, your \"Wild\" rating encompasses all of the \
                        following variants at all time controls:\n") +
                        ", ".join([gt.display_text for gt in WildGameType.instances()]))
                table.attach(label(rating[ELO], xalign=1), col, col + 1, row, row + 1)
                col += 1
                if not my_finger:
                    table.attach(label(rating[DEVIATION], xalign=1), col, col + 1, row, row + 1)
                    col += 1
                table.attach(label(rating[WINS], xalign=1), col, col + 1, row, row + 1)
                col += 1
                table.attach(label(rating[DRAWS], xalign=1), col, col + 1, row, row + 1)
                col += 1
                table.attach(label(rating[LOSSES], xalign=1), col, col + 1, row, row + 1)
                col += 1
                if not my_finger and len(rating) > BESTELO:
                    best = rating[BESTELO] if int(rating[BESTELO]) > 0 else ""
                    table.attach(label(best, xalign=1), col, col + 1, row, row + 1)
                    col += 1
                    table.attach(label(rating[BESTTIME], xalign=1), col, col + 1, row, row + 1)
                    col += 1
                row += 1

            table.attach(Gtk.HSeparator(), 0, cols, row, row + 1, ypadding=2)
            row += 1

        if finger.getSanctions() != "":
            table.attach(label(_("Sanctions") + ":", is_error=True), 0, 1, row, row + 1)
            table.attach(label(finger.getSanctions()), 1, cols, row, row + 1)
            row += 1

        if finger.getEmail():
            table.attach(label(_("Email") + ":"), 0, 1, row, row + 1)
            table.attach(label(finger.getEmail()), 1, cols, row, row + 1)
            row += 1

        player = self.connection.players.get(finger.getName())
        if not player.isGuest():
            table.attach(label(_("Games") + ":"), 0, 1, row, row + 1)
            llabel = Gtk.Label()
            llabel.props.xalign = 0
            link = "http://ficsgames.org/cgi-bin/search.cgi?player=%s" % finger.getName()
            llabel.set_markup('<a href="%s">%s</a>' % (link, link))
            table.attach(llabel, 1, cols, row, row + 1)
            row += 1

        if finger.getCreated():
            table.attach(label(_("Spent") + ":"), 0, 1, row, row + 1)
            string = "%s %s" % (finger.getTotalTimeOnline(), _("online in total"))
            table.attach(label(string), 1, cols, row, row + 1)
            row += 1

        # TODO: ping causes random crashes on Windows
        if my_finger and sys.platform != "win32":
            table.attach(label(_("Ping") + ":"), 0, 1, row, row + 1)
            if self.ping_label:
                if self.dock.get_children():
                    self.dock.get_children()[0].remove(self.ping_label)
            else:
                self.ping_label = Gtk.Label(label=_("Connecting") + "...")
                self.ping_label.props.xalign = 0

            @idle_add
            def callback(pinger, pingtime):
                log.debug("'%s' '%s'" % (str(self.pinger), str(pingtime)),
                          extra={"task": (self.connection.username,
                                          "UIS.oF.callback")})
                if isinstance(pingtime, str):
                    self.ping_label.set_text(pingtime)
                elif pingtime == -1:
                    self.ping_label.set_text(_("Unknown"))
                else:
                    self.ping_label.set_text("%.0f ms" % pingtime)

            if not self.pinger:
                self.pinger = Pinger(self.host)
                self.pinger.start()
                self.pinger.connect("received", callback)
                self.pinger.connect("error", callback)
            table.attach(self.ping_label, 1, cols, row, row + 1)
            row += 1

        if not my_finger:
            if self.lounge.finger_sent:
                dialog = Gtk.MessageDialog(type=Gtk.MessageType.INFO,
                                           buttons=Gtk.ButtonsType.OK)
                dialog.set_title(_("Finger"))
                dialog.set_markup("<b>%s</b>" % finger.getName())
                table.show_all()
                dialog.get_message_area().add(table)
                dialog.run()
                dialog.destroy()
            self.lounge.finger_sent = False
            return

        if not self.connection.isRegistred():
            vbox = Gtk.VBox()
            table.attach(vbox, 0, cols, row, row + 1)
            label0 = Gtk.Label()
            label0.props.xalign = 0
            label0.props.wrap = True
            label0.props.width_request = 300
            label0.set_markup(_("You are currently logged in as a guest.\n" +
                                "A guest can't play rated games and therefore isn't " +
                                "able to play as many of the types of matches offered as " +
                                "a registered user. To register an account, go to " +
                                "<a href=\"http://www.freechess.org/Register/index.html\">" +
                                "http://www.freechess.org/Register/index.html</a>."))
            vbox.add(label0)

        if self.dock.get_children():
            self.dock.remove(self.dock.get_children()[0])
        self.dock.add(table)
        self.dock.show_all()


class NewsSection(Section):

    def __init__(self, widgets, connection):
        self.widgets = widgets
        connection.nm.connect("readNews", self.onNewsItem)

    @idle_add
    def onNewsItem(self, nm, news):
        weekday, month, day, title, details = news

        dtitle = "%s, %s %s: %s" % (weekday, month, day, title)
        label = Gtk.Label(label=dtitle)
        label.props.width_request = 300
        label.props.xalign = 0
        label.set_ellipsize(Pango.EllipsizeMode.END)
        expander = Gtk.Expander()
        expander.set_label_widget(label)
        expander.set_tooltip_text(title)
        textview = Gtk.TextView()
        textview.set_wrap_mode(Gtk.WrapMode.WORD)
        textview.set_editable(False)
        textview.set_cursor_visible(False)
        textview.props.pixels_above_lines = 4
        textview.props.pixels_below_lines = 4
        textview.props.right_margin = 2
        textview.props.left_margin = 6
        uistuff.initTexviewLinks(textview, details)

        alignment = Gtk.Alignment()
        alignment.set_padding(3, 6, 12, 0)
        alignment.props.xscale = 1
        alignment.add(textview)

        expander.add(alignment)
        expander.show_all()
        self.widgets["newsVBox"].pack_end(expander, True, True, 0)


SEPARATOR, ACCEPT, ASSESS, OBSERVE, FOLLOW, CHAT, CHALLENGE, FINGER, ARCHIVED = range(9)


class ParrentListSection(Section):
    """ Parrent for sections mainly consisting of a large treeview """

    def button_press_event(self, treeview, event):
        if event.button == 3:  # right click
            pathinfo = treeview.get_path_at_pos(int(event.x), int(event.y))
            if pathinfo is not None:
                path, col = pathinfo[0], pathinfo[1]
                treeview.grab_focus()
                treeview.set_cursor(path, col, 0)
                self.menu.show_all()
                self.menu.popup(None, None, None, None, event.button,
                                Gtk.get_current_event_time())
            return True
        return False

    def createLocalMenu(self, items):
        ITEM_MAP = {
            ACCEPT: (_("Accept"), self.on_accept),
            ASSESS: (_("Assess"), self.on_assess),
            OBSERVE: (_("Observe"), self.on_observe),
            FOLLOW: (_("Follow"), self.on_follow),
            CHAT: (_("Chat"), self.on_chat),
            CHALLENGE: (_("Challenge"), self.on_challenge),
            FINGER: (_("Finger"), self.on_finger),
            ARCHIVED: (_("Archived"), self.on_archived), }

        self.menu = Gtk.Menu()
        for item in items:
            if item == SEPARATOR:
                menu_item = Gtk.SeparatorMenuItem()
            else:
                label, callback = ITEM_MAP[item]
                menu_item = Gtk.MenuItem(label)
                menu_item.connect("activate", callback)
            self.menu.append(menu_item)
        self.menu.attach_to_widget(self.tv, None)

    def addColumns(self, treeview, *columns, **keyargs):
        if "hide" in keyargs:
            hide = keyargs["hide"]
        else:
            hide = []
        if "pix" in keyargs:
            pix = keyargs["pix"]
        else:
            pix = []
        for i, name in enumerate(columns):
            if i in hide:
                continue
            if i in pix:
                crp = Gtk.CellRendererPixbuf()
                crp.props.xalign = .5
                column = Gtk.TreeViewColumn(name, crp, pixbuf=i)
            else:
                crt = Gtk.CellRendererText()
                column = Gtk.TreeViewColumn(name, crt, text=i)
                column.set_resizable(True)
            column.set_sort_column_id(i)
            # prevent columns appear choppy
            column.set_sizing(Gtk.TreeViewColumnSizing.GROW_ONLY)

            column.set_reorderable(True)
            treeview.append_column(column)

    def lowLeftSearchPosFunc(self, tv, search_dialog, user_data):
        alloc = tv.get_allocation()
        window = tv.get_toplevel().get_window()
        x_loc = alloc.x + window.get_position()[0]
        y_loc = alloc.y + window.get_position()[1] + alloc.height
        search_dialog.move(x_loc, y_loc)
        search_dialog.show_all()

    def pixCompareFunction(self, treemodel, iter0, iter1, column):
        pix0 = treemodel.get_value(iter0, column)
        pix1 = treemodel.get_value(iter1, column)
        if isinstance(pix0, GdkPixbuf.Pixbuf) and isinstance(pix1,
                                                             GdkPixbuf.Pixbuf):
            return cmp(pix0.get_pixels(), pix1.get_pixels())
        return cmp(pix0, pix1)

    def timeCompareFunction(self, treemodel, iter0, iter1, column):
        (minute0, minute1) = (treemodel.get_value(iter0, 8),
                              treemodel.get_value(iter1, 8))
        return cmp(minute0, minute1)

    def on_accept(self, button):
        model, sel_iter = self.tv.get_selection().get_selected()
        if sel_iter is None:
            return
        sought = model.get_value(sel_iter, 0)
        if isinstance(sought, FICSChallenge):
            self.connection.om.acceptIndex(sought.index)
        else:
            self.connection.om.playIndex(sought.index)

        try:
            message = self.messages[hash(sought)]
        except KeyError:
            pass
        else:
            message.dismiss()
            del self.messages[hash(sought)]

    def on_assess(self, widget):
        model, sel_iter = self.tv.get_selection().get_selected()
        if sel_iter is None:
            return
        sought = model.get_value(sel_iter, 0)
        player1 = self.connection.username
        player2 = sought.player.name
        game_type = sought.game_type.short_fics_name
        self.connection.glm.assess(player1, player2, game_type)
        self.assess_sent = True

    def on_observe(self, widget, *args):
        player = self.getSelectedPlayer()
        if player is not None:
            if player.game is not None:
                self.connection.bm.observe(player.game)
            else:
                self.connection.bm.observe(None, player=player)

    def on_follow(self, widget):
        player = self.getSelectedPlayer()
        if player is not None:
            self.connection.bm.follow(player)

    def on_chat(self, button):
        player = self.getSelectedPlayer()
        if player is None:
            return
        self.lounge.chat.openChatWithPlayer(player.name)
        # TODO: isadmin og type

    def on_challenge(self, widget):
        player = self.getSelectedPlayer()
        if player is not None:
            self.lounge.seek_challenge.onChallengeButtonClicked(widget, player)

    def on_finger(self, widget):
        player = self.getSelectedPlayer()
        if player is not None:
            self.connection.fm.finger(player.name)
            self.lounge.finger_sent = True

    def on_archived(self, widget):
        player = self.getSelectedPlayer()
        if player is not None:
            self.connection.adm.queryAdjournments(player.name)
            self.connection.adm.queryHistory(player.name)
            self.connection.adm.queryJournal(player.name)

            notebook = self.widgets["notebook"]
            archived = self.widgets["archiveListContent"]
            notebook.set_current_page(notebook.page_num(archived))


class SeekTabSection(ParrentListSection):

    def __init__(self, widgets, connection, lounge):
        self.widgets = widgets
        self.connection = connection
        self.lounge = lounge
        self.infobar = lounge.infobar
        self.messages = {}
        self.seeks = {}
        self.challenges = {}
        self.seekPix = get_pixbuf("glade/seek.png")
        self.chaPix = get_pixbuf("glade/challenge.png")
        self.manSeekPix = get_pixbuf("glade/manseek.png")

        self.widgets["seekExpander"].set_vexpand(False)

        self.tv = self.widgets["seektreeview"]
        self.store = Gtk.ListStore(FICSSoughtMatch, GdkPixbuf.Pixbuf,
                                   GdkPixbuf.Pixbuf, str, int, str, str, str,
                                   int, Gdk.RGBA, str)
        self.model = Gtk.TreeModelSort(model=self.store)
        self.tv.set_model(self.model)
        self.addColumns(self.tv,
                        "FICSSoughtMatch",
                        "",
                        "",
                        _("Name"),
                        _("Rating"),
                        _("Rated"),
                        _("Type"),
                        _("Clock"),
                        "gametime",
                        "textcolor",
                        "tooltip",
                        hide=[0, 8, 9, 10],
                        pix=[1, 2])
        self.tv.set_search_column(3)
        self.tv.set_tooltip_column(10, )
        for i in range(0, 2):
            self.tv.get_model().set_sort_func(i, self.pixCompareFunction,
                                              i + 1)
        for i in range(2, 8):
            self.tv.get_model().set_sort_func(i, self.compareFunction, i)
        try:
            self.tv.set_search_position_func(self.lowLeftSearchPosFunc, None)
        except AttributeError:
            # Unknow signal name is raised by gtk < 2.10
            pass
        for num in range(2, 7):
            column = self.tv.get_column(num)
            for cellrenderer in column.get_cells():
                column.add_attribute(cellrenderer, "foreground_rgba", 9)
        self.selection = self.tv.get_selection()
        self.lastSeekSelected = None
        self.selection.set_select_function(self.selectFunction, True)
        self.selection.connect("changed", self.onSelectionChanged)
        self.widgets["clearSeeksButton"].connect("clicked",
                                                 self.onClearSeeksClicked)
        self.widgets["acceptButton"].connect("clicked", self.on_accept)
        self.widgets["declineButton"].connect("clicked", self.onDeclineClicked)
        self.tv.connect("row-activated", self.row_activated)
        self.tv.connect('button-press-event', self.button_press_event)

        self.connection.seeks.connect("FICSSeekCreated", self.onAddSeek)
        self.connection.seeks.connect("FICSSeekRemoved", self.onRemoveSeek)
        self.connection.challenges.connect("FICSChallengeIssued",
                                           self.onChallengeAdd)
        self.connection.challenges.connect("FICSChallengeRemoved",
                                           self.onChallengeRemove)
        self.connection.glm.connect("our-seeks-removed",
                                    self.our_seeks_removed)
        self.connection.glm.connect("assessReceived", self.onAssessReceived)
        self.connection.bm.connect("playGameCreated", self.onPlayingGame)
        self.connection.bm.connect("curGameEnded", self.onCurGameEnded)

        def get_sort_order(modelsort):
            identity, order = modelsort.get_sort_column_id()
            if identity is None or identity < 0:
                identity = 0
            else:
                identity += 1
            if order == Gtk.SortType.DESCENDING:
                identity = -1 * identity
            return identity

        def set_sort_order(modelsort, value):
            if value != 0:
                order = Gtk.SortType.ASCENDING if value > 0 else Gtk.SortType.DESCENDING
                modelsort.set_sort_column_id(abs(value) - 1, order)

        uistuff.keep(self.model, "seektreeview_sort_order_col", get_sort_order,
                     lambda modelsort, value: set_sort_order(modelsort, value))

        self.createLocalMenu((ACCEPT, ASSESS, CHALLENGE, CHAT, FOLLOW, SEPARATOR, FINGER, ARCHIVED))
        self.assess_sent = False

    @idle_add
    def onAssessReceived(self, glm, assess):
        if self.assess_sent:
            self.assess_sent = False
            dialog = Gtk.MessageDialog(type=Gtk.MessageType.INFO,
                                       buttons=Gtk.ButtonsType.OK)
            dialog.set_title(_("Assess"))
            dialog.set_markup(_("Effect on ratings by the possible outcomes"))
            grid = Gtk.Grid()
            grid.set_column_homogeneous(True)
            grid.set_row_spacing(12)
            grid.set_row_spacing(12)
            name0 = Gtk.Label()
            name0.set_markup("<b>%s</b>" % assess["names"][0])
            name1 = Gtk.Label()
            name1.set_markup("<b>%s</b>" % assess["names"][1])
            grid.attach(Gtk.Label(""), 0, 0, 1, 1)
            grid.attach(name0, 1, 0, 1, 1)
            grid.attach(name1, 2, 0, 1, 1)
            grid.attach(Gtk.Label(assess["type"]), 0, 1, 1, 1)
            grid.attach(Gtk.Label(assess["oldRD"][0]), 1, 1, 1, 1)
            grid.attach(Gtk.Label(assess["oldRD"][1]), 2, 1, 1, 1)
            grid.attach(Gtk.Label(_("Win:")), 0, 2, 1, 1)
            grid.attach(Gtk.Label(assess["win"][0]), 1, 2, 1, 1)
            grid.attach(Gtk.Label(assess["win"][1]), 2, 2, 1, 1)
            grid.attach(Gtk.Label(_("Draw:")), 0, 3, 1, 1)
            grid.attach(Gtk.Label(assess["draw"][0]), 1, 3, 1, 1)
            grid.attach(Gtk.Label(assess["draw"][1]), 2, 3, 1, 1)
            grid.attach(Gtk.Label(_("Loss:")), 0, 4, 1, 1)
            grid.attach(Gtk.Label(assess["loss"][0]), 1, 4, 1, 1)
            grid.attach(Gtk.Label(assess["loss"][1]), 2, 4, 1, 1)
            grid.attach(Gtk.Label(_("New RD:")), 0, 5, 1, 1)
            grid.attach(Gtk.Label(assess["newRD"][0]), 1, 5, 1, 1)
            grid.attach(Gtk.Label(assess["newRD"][1]), 2, 5, 1, 1)
            grid.show_all()
            dialog.get_message_area().add(grid)
            dialog.run()
            dialog.destroy()

    def getSelectedPlayer(self):
        model, sel_iter = self.tv.get_selection().get_selected()
        if sel_iter is not None:
            sought = model.get_value(sel_iter, 0)
            return sought.player

    def textcolor_normal(self):
        style_ctxt = self.tv.get_style_context()
        return style_ctxt.get_color(Gtk.StateFlags.NORMAL)

    def textcolor_selected(self):
        style_ctxt = self.tv.get_style_context()
        return style_ctxt.get_color(Gtk.StateFlags.INSENSITIVE)

    def selectFunction(self, selection, model, path, is_selected, data):
        if model[path][9] == self.textcolor_selected():
            return False
        else:
            return True

    def __isAChallengeOrOurSeek(self, row):
        sought = row[0]
        textcolor = row[9]
        red0, green0, blue0 = textcolor.red, textcolor.green, textcolor.blue
        selected = self.textcolor_selected()
        red1, green1, blue1 = selected.red, selected.green, selected.blue
        if (isinstance(sought, FICSChallenge)) or (red0 == red1 and green0 == green1 and
                                                   blue0 == blue1):
            return True
        else:
            return False

    def compareFunction(self, model, iter0, iter1, column):
        row0 = list(model[model.get_path(iter0)])
        row1 = list(model[model.get_path(iter1)])
        is_ascending = True if self.tv.get_column(column - 1).get_sort_order() is \
            Gtk.SortType.ASCENDING else False
        if self.__isAChallengeOrOurSeek(
                row0) and not self.__isAChallengeOrOurSeek(row1):
            if is_ascending:
                return -1
            else:
                return 1
        elif self.__isAChallengeOrOurSeek(
                row1) and not self.__isAChallengeOrOurSeek(row0):
            if is_ascending:
                return 1
            else:
                return -1
        elif column is 7:
            return self.timeCompareFunction(model, iter0, iter1, column)
        else:
            value0 = row0[column]
            value0 = value0.lower() if isinstance(value0, str) else value0
            value1 = row1[column]
            value1 = value1.lower() if isinstance(value1, str) else value1
            return cmp(value0, value1)

    def __updateActiveSeeksLabel(self):
        count = len(self.seeks) + len(self.challenges)
        self.widgets["activeSeeksLabel"].set_text(_("Active seeks: %d") %
                                                  count)

    @idle_add
    def onAddSeek(self, seeks, seek):
        log.debug("%s" % seek,
                  extra={"task": (self.connection.username, "onAddSeek")})
        pix = self.seekPix if seek.automatic else self.manSeekPix
        textcolor = self.textcolor_selected() if seek.player.name == self.connection.getUsername() \
            else self.textcolor_normal()
        seek_ = [seek, seek.player.getIcon(gametype=seek.game_type), pix,
                 seek.player.name + seek.player.display_titles(),
                 seek.player_rating, seek.display_rated,
                 seek.game_type.display_text, seek.display_timecontrol,
                 seek.sortable_time, textcolor, get_seek_tooltip_text(seek)]

        if textcolor == self.textcolor_selected():
            txi = self.store.prepend(seek_)
            self.tv.scroll_to_cell(self.store.get_path(txi))
            self.widgets["clearSeeksButton"].set_sensitive(True)
        else:
            txi = self.store.append(seek_)
        self.seeks[hash(seek)] = txi
        self.__updateActiveSeeksLabel()

    @idle_add
    def onRemoveSeek(self, seeks, seek):
        log.debug("%s" % seek,
                  extra={"task": (self.connection.username, "onRemoveSeek")})
        try:
            treeiter = self.seeks[hash(seek)]
        except KeyError:
            # We ignore removes we haven't added, as it seems fics sends a
            # lot of removes for games it has never told us about
            return
        if self.store.iter_is_valid(treeiter):
            self.store.remove(treeiter)
        del self.seeks[hash(seek)]
        self.__updateActiveSeeksLabel()

    @idle_add
    def onChallengeAdd(self, challenges, challenge):
        log.debug("%s" % challenge,
                  extra={"task": (self.connection.username, "onChallengeAdd")})
        SoundTab.playAction("aPlayerChecks")

        # TODO: differentiate between challenges and manual-seek-accepts
        # (wait until seeks are comparable FICSSeek objects to do this)
        # Related: http://code.google.com/p/pychess/issues/detail?id=206
        if challenge.adjourned:
            text = _(" would like to resume your adjourned <b>%(time)s</b> " +
                     "<b>%(gametype)s</b> game.") % \
                {"time": challenge.display_timecontrol,
                 "gametype": challenge.game_type.display_text}
        else:
            text = _(" challenges you to a <b>%(time)s</b> %(rated)s <b>%(gametype)s</b> game") \
                % {"time": challenge.display_timecontrol,
                   "rated": challenge.display_rated.lower(),
                   "gametype": challenge.game_type.display_text}
            if challenge.color:
                text += _(" where <b>%(player)s</b> plays <b>%(color)s</b>.") \
                    % {"player": challenge.player.name,
                       "color": _("white") if challenge.color == "white" else _("black")}
            else:
                text += "."
        content = get_infobarmessage_content(challenge.player,
                                             text,
                                             gametype=challenge.game_type)

        @idle_add
        def callback(infobar, response, message):
            if response == Gtk.ResponseType.ACCEPT:
                self.connection.om.acceptIndex(challenge.index)
            elif response == Gtk.ResponseType.NO:
                self.connection.om.declineIndex(challenge.index)
            message.dismiss()
            return False

        message = InfoBarMessage(Gtk.MessageType.QUESTION, content, callback)
        message.add_button(InfoBarMessageButton(
            _("Accept"), Gtk.ResponseType.ACCEPT))
        message.add_button(InfoBarMessageButton(
            _("Decline"), Gtk.ResponseType.NO))
        message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                Gtk.ResponseType.CANCEL))
        self.messages[hash(challenge)] = message
        self.infobar.push_message(message)

        txi = self.store.prepend(
            [challenge, challenge.player.getIcon(gametype=challenge.game_type),
             self.chaPix, challenge.player.name +
             challenge.player.display_titles(), challenge.player_rating,
             challenge.display_rated, challenge.game_type.display_text,
             challenge.display_timecontrol, challenge.sortable_time,
             self.textcolor_normal(), get_challenge_tooltip_text(challenge)])
        self.challenges[hash(challenge)] = txi
        self.__updateActiveSeeksLabel()
        self.widgets["seektreeview"].scroll_to_cell(self.store.get_path(txi))

    @idle_add
    def onChallengeRemove(self, challenges, challenge):
        log.debug(
            "%s" % challenge,
            extra={"task": (self.connection.username, "onChallengeRemove")})
        try:
            txi = self.challenges[hash(challenge)]
        except KeyError:
            pass
        else:
            if self.store.iter_is_valid(txi):
                self.store.remove(txi)
            del self.challenges[hash(challenge)]

        try:
            message = self.messages[hash(challenge)]
        except KeyError:
            pass
        else:
            message.dismiss()
            del self.messages[hash(challenge)]
        self.__updateActiveSeeksLabel()

    @idle_add
    def our_seeks_removed(self, glm):
        self.widgets["clearSeeksButton"].set_sensitive(False)

    def onDeclineClicked(self, button):
        model, sel_iter = self.tv.get_selection().get_selected()
        if sel_iter is None:
            return
        sought = model.get_value(sel_iter, 0)
        self.connection.om.declineIndex(sought.index)

        try:
            message = self.messages[hash(sought)]
        except KeyError:
            pass
        else:
            message.dismiss()
            del self.messages[hash(sought)]

    def onClearSeeksClicked(self, button):
        self.connection.client.run_command("unseek")
        self.widgets["clearSeeksButton"].set_sensitive(False)

    def row_activated(self, treeview, path, view_column):
        model, sel_iter = self.tv.get_selection().get_selected()
        if sel_iter is None:
            return
        sought = model.get_value(sel_iter, 0)
        if self.lastSeekSelected is None or \
                sought.index != self.lastSeekSelected.index:
            return
        if path != model.get_path(sel_iter):
            return
        self.on_accept(None)

    def onSelectionChanged(self, selection):
        model, sel_iter = selection.get_selected()
        sought = None
        a_seek_is_selected = False
        selection_is_challenge = False
        if sel_iter is not None:
            a_seek_is_selected = True
            sought = model.get_value(sel_iter, 0)
            if isinstance(sought, FICSChallenge):
                selection_is_challenge = True

            # # select sought owner on players tab to let challenge him using right click menu
            # if sought.player in self.lounge.players_tab.players:
                # # we have to undo the iter conversion that was introduced by the filter and sort model
                # iter0 = self.lounge.players_tab.players[sought.player]["ti"]
                # filtered_model = self.lounge.players_tab.player_filter
                # is_ok, iter1 = filtered_model.convert_child_iter_to_iter(iter0)
                # sorted_model = self.lounge.players_tab.model
                # is_ok, iter2 = sorted_model.convert_child_iter_to_iter(iter1)
                # players_selection = self.lounge.players_tab.tv.get_selection()
                # players_selection.select_iter(iter2)
                # self.lounge.players_tab.tv.scroll_to_cell(sorted_model.get_path(iter2))
            # else:
                # print(sought.player, "not in self.lounge.players_tab.players")

        self.lastSeekSelected = sought
        self.widgets["acceptButton"].set_sensitive(a_seek_is_selected)
        self.widgets["declineButton"].set_sensitive(selection_is_challenge)

    def _clear_messages(self):
        for message in self.messages.values():
            message.dismiss()
        self.messages.clear()

    @idle_add
    def onPlayingGame(self, bm, game):
        self._clear_messages()
        self.widgets["seekListContent"].set_sensitive(False)
        self.widgets["clearSeeksButton"].set_sensitive(False)
        self.__updateActiveSeeksLabel()

    @idle_add
    def onCurGameEnded(self, bm, game):
        self.widgets["seekListContent"].set_sensitive(True)


YMARKS = (800, 1600, 2400)
# YLOCATION = lambda y: min(y / 3000., 3000)
XMARKS = (5, 15)
# XLOCATION = lambda x: e**(-6.579 / (x + 1))


def YLOCATION(y):
    return min(y / 3000., 3000)


def XLOCATION(x):
    return e**(-6.579 / (x + 1))


# This is used to convert increment time to minutes. With a GAME_LENGTH on
# 40, a game on two minutes and twelve secconds will be placed at the same
# X location as a game on 2+12*40/60 = 10 minutes
GAME_LENGTH = 40


class SeekGraphSection(ParrentListSection):

    def __init__(self, widgets, connection, lounge):
        self.widgets = widgets
        self.connection = connection
        self.graph = SpotGraph()

        for rating in YMARKS:
            self.graph.addYMark(YLOCATION(rating), str(rating))
        for mins in XMARKS:
            self.graph.addXMark(XLOCATION(mins), str(mins) + _(" min"))

        self.widgets["graphDock"].add(self.graph)
        self.graph.show()
        self.graph.connect("spotClicked", self.onSpotClicked)

        self.connection.seeks.connect("FICSSeekCreated", self.onAddSought)
        self.connection.seeks.connect("FICSSeekRemoved", self.onRemoveSought)
        self.connection.challenges.connect("FICSChallengeIssued",
                                           self.onAddSought)
        self.connection.challenges.connect("FICSChallengeRemoved",
                                           self.onRemoveSought)
        self.connection.bm.connect("playGameCreated", self.onPlayingGame)
        self.connection.bm.connect("curGameEnded", self.onCurGameEnded)

    def onSpotClicked(self, graph, name):
        self.connection.bm.play(name)

    @idle_add
    def onAddSought(self, manager, sought):
        log.debug("%s" % sought,
                  extra={"task": (self.connection.username, "onAddSought")})
        x_loc = XLOCATION(float(sought.minutes) +
                          float(sought.inc) * GAME_LENGTH / 60.)
        y_loc = YLOCATION(float(sought.player_rating))
        if ((sought.rated) and ('(C)' in sought.player.long_name())):
            type_ = 2
        elif (not (sought.rated) and ('(C)' in sought.player.long_name())):
            type_ = 3
        elif sought.rated:
            type_ = 0
        else:
            type_ = 1

        if isinstance(sought, FICSChallenge):
            tooltip_text = get_challenge_tooltip_text(sought)
        else:
            tooltip_text = get_seek_tooltip_text(sought)
        self.graph.addSpot(sought.index, tooltip_text, x_loc, y_loc, type_)

    @idle_add
    def onRemoveSought(self, manager, sought):
        log.debug("%s" % sought,
                  extra={"task": (self.connection.username, "onRemoveSought")})
        self.graph.removeSpot(sought.index)

    @idle_add
    def onPlayingGame(self, bm, game):
        self.widgets["seekGraphContent"].set_sensitive(False)

    @idle_add
    def onCurGameEnded(self, bm, game):
        self.widgets["seekGraphContent"].set_sensitive(True)


class PlayerTabSection(ParrentListSection):

    widgets = []

    def __init__(self, widgets, connection, lounge):
        PlayerTabSection.widgets = widgets
        self.connection = connection
        self.lounge = lounge
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
            initial = conf.get(widget, True)
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

    @idle_add
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

    @idle_add
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

        def update_gui():
            self.onSelectionChanged(self.tv.get_selection())

        idle_add(update_gui)
        return False

    @idle_add
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


class GameTabSection(ParrentListSection):

    def __init__(self, widgets, connection, lounge):
        self.widgets = widgets
        self.connection = connection
        self.lounge = lounge
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
            initial = conf.get(widget, True)
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

    def game_filter_func(self, model, iter, data):
        game = model[iter][0]
        is_standard = game.game_type.rating_type == TYPE_STANDARD
        is_blitz = game.game_type.rating_type == TYPE_BLITZ
        is_lightning = game.game_type.rating_type == TYPE_LIGHTNING
        is_variant = game.game_type.rating_type in RATING_TYPES[3:]
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

    @idle_add
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

    @idle_add
    def onGameObserved(self, bm, game):
        if game in self.games:
            treeiter = self.games[game]["ti"]
            self.store.set_value(treeiter, 1, self.recpix)

    @idle_add
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


class AdjournedTabSection(ParrentListSection):

    def __init__(self, widgets, connection, lounge):
        self.connection = connection
        self.widgets = widgets
        self.lounge = lounge
        self.infobar = lounge.infobar
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

    @idle_add
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

    @idle_add
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

    @idle_add
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

    @idle_add
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

    @idle_add
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

    @idle_add
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

    @idle_add
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

    @idle_add
    def onHistoryGameRemoved(self, adm, game):
        if game in self.games:
            if self.store.iter_is_valid(self.games[game]["ti"]):
                self.store.remove(self.games[game]["ti"])
            del self.games[game]

        return False

    @idle_add
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

    @idle_add
    def onGamePreview(self, adm, ficsgame):
        log.debug("ICLounge.onGamePreview: %s" % ficsgame)

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

        game_handler.generalStart(gamemodel, player0tup, player1tup, (
            StringIO(ficsgame.board.pgn), pgn, 0, -1))
        gamemodel.connect("game_started", self.on_game_start, ficsgame)

    def on_game_start(self, gamemodel, ficsgame):
        gamemodel.end(ficsgame.result, ficsgame.reason)

RATING_SLIDER_STEP = 25


class SeekChallengeSection(Section):

    seekEditorWidgets = (
        "untimedCheck",
        "minutesSpin",
        "gainSpin",
        "strengthCheck",
        "chainAlignment",
        "ratingCenterSlider",
        "toleranceSlider",
        "toleranceHBox",
        "nocolorRadio",
        "whitecolorRadio",
        "blackcolorRadio",
        # variantCombo has to come before other variant widgets so that
        # when the widget is loaded, variantRadio isn't selected by the callback,
        # overwriting the user's saved value for the variant radio buttons
        "variantCombo",
        "noVariantRadio",
        "variantRadio",
        "ratedGameCheck",
        "manualAcceptCheck")

    seekEditorWidgetDefaults = {
        "untimedCheck": [False, False, False],
        "minutesSpin": [15, 5, 2],
        "gainSpin": [10, 0, 1],
        "strengthCheck": [False, True, False],
        "chainAlignment": [True, True, True],
        "ratingCenterSlider": [40, 40, 40],
        "toleranceSlider": [8, 8, 8],
        "toleranceHBox": [False, False, False],
        "variantCombo": [RANDOMCHESS, FISCHERRANDOMCHESS, LOSERSCHESS],
        "noVariantRadio": [True, False, True],
        "variantRadio": [False, True, False],
        "nocolorRadio": [True, True, True],
        "whitecolorRadio": [False, False, False],
        "blackcolorRadio": [False, False, False],
        "ratedGameCheck": [False, True, True],
        "manualAcceptCheck": [False, False, False],
    }

    seekEditorWidgetGettersSetters = {}

    def __init__(self, lounge):
        self.lounge = lounge
        self.widgets = lounge.widgets
        self.connection = lounge.connection

        self.finger = None
        conf.set("numberOfFingers", 0)
        self.connection.fm.connect("fingeringFinished", self.onFinger)
        self.connection.fm.finger(self.connection.getUsername())

        self.widgets["untimedCheck"].connect("toggled",
                                             self.onUntimedCheckToggled)
        self.widgets["minutesSpin"].connect("value-changed",
                                            self.onTimeSpinChanged)
        self.widgets["gainSpin"].connect("value-changed",
                                         self.onTimeSpinChanged)
        self.onTimeSpinChanged(self.widgets["minutesSpin"])

        self.widgets["nocolorRadio"].connect("toggled",
                                             self.onColorRadioChanged)
        self.widgets["whitecolorRadio"].connect("toggled",
                                                self.onColorRadioChanged)
        self.widgets["blackcolorRadio"].connect("toggled",
                                                self.onColorRadioChanged)
        self.onColorRadioChanged(self.widgets["nocolorRadio"])

        self.widgets["noVariantRadio"].connect("toggled",
                                               self.onVariantRadioChanged)
        self.widgets["variantRadio"].connect("toggled",
                                             self.onVariantRadioChanged)
        variantcombo = self.widgets["variantCombo"]
        variantcombo.set_name("variantcombo")
        variantComboGetter, variantComboSetter = self.__initVariantCombo(
            variantcombo)
        self.seekEditorWidgetGettersSetters["variantCombo"] = (
            variantComboGetter, variantComboSetter)
        self.widgets["variantCombo"].connect("changed",
                                             self.onVariantComboChanged)

        self.widgets["editSeekDialog"].connect("delete_event", lambda *a: True)
        #        self.widgets["challengeDialog"].connect("delete_event", lambda *a: True)

        self.widgets["strengthCheck"].connect("toggled",
                                              self.onStrengthCheckToggled)
        self.onStrengthCheckToggled(self.widgets["strengthCheck"])
        self.widgets["ratingCenterSlider"].connect(
            "value-changed", self.onRatingCenterSliderChanged)
        self.onRatingCenterSliderChanged(self.widgets["ratingCenterSlider"])
        self.widgets["toleranceSlider"].connect("value-changed",
                                                self.onToleranceSliderChanged)
        self.onToleranceSliderChanged(self.widgets["toleranceSlider"])
        self.widgets["toleranceButton"].connect("clicked",
                                                self.onToleranceButtonClicked)
        self.widgets["toleranceButton"].connect("activate-link",
                                                lambda link_button: True)

        def intGetter(widget):
            return int(widget.get_value())

        self.seekEditorWidgetGettersSetters["minutesSpin"] = (intGetter, None)
        self.seekEditorWidgetGettersSetters["gainSpin"] = (intGetter, None)
        self.seekEditorWidgetGettersSetters["ratingCenterSlider"] = \
            (intGetter, None)
        self.seekEditorWidgetGettersSetters["toleranceSlider"] = \
            (intGetter, None)

        def toleranceHBoxGetter(widget):
            return self.widgets["toleranceHBox"].get_property("visible")

        def toleranceHBoxSetter(widget, visible):
            assert isinstance(visible, bool)
            if visible:
                self.widgets["toleranceHBox"].show()
            else:
                self.widgets["toleranceHBox"].hide()

        self.seekEditorWidgetGettersSetters["toleranceHBox"] = (
            toleranceHBoxGetter, toleranceHBoxSetter)

        self.chainbox = ChainVBox()
        self.widgets["chainAlignment"].add(self.chainbox)

        def chainboxGetter(widget):
            return self.chainbox.active

        def chainboxSetter(widget, is_active):
            self.chainbox.active = is_active

        self.seekEditorWidgetGettersSetters["chainAlignment"] = (
            chainboxGetter, chainboxSetter)

        self.challengee = None
        self.in_challenge_mode = False
        self.seeknumber = 1
        self.widgets["seekButton"].connect("clicked", self.onSeekButtonClicked)
        self.widgets["seekAllButton"].connect("clicked",
                                              self.onSeekAllButtonClicked)
        self.widgets["challengeButton"].connect("clicked",
                                                self.onChallengeButtonClicked)
        self.widgets["challengeDialog"].connect("delete-event",
                                                self.onChallengeDialogResponse)
        self.widgets["challengeDialog"].connect("response",
                                                self.onChallengeDialogResponse)
        self.widgets["editSeekDialog"].connect("response",
                                               self.onEditSeekDialogResponse)

        for widget in ("seek1Radio", "seek2Radio", "seek3Radio",
                       "challenge1Radio", "challenge2Radio",
                       "challenge3Radio"):
            uistuff.keep(self.widgets[widget], widget)

        self.lastdifference = 0
        self.loading_seek_editor = False
        self.savedSeekRadioTexts = [GAME_TYPES["blitz"].display_text] * 3

        for i in range(1, 4):
            self.__loadSeekEditor(i)
            self.__writeSavedSeeks(i)
            self.widgets["seek%sRadioConfigButton" % i].connect(
                "clicked", self.onSeekRadioConfigButtonClicked, i)
            self.widgets["challenge%sRadioConfigButton" % i].connect(
                "clicked", self.onChallengeRadioConfigButtonClicked, i)

        if not self.connection.isRegistred():
            self.chainbox.active = False
            self.widgets["chainAlignment"].set_sensitive(False)
            self.widgets["chainAlignment"].set_tooltip_text(_(
                "The chain button is disabled because you are logged in as a guest. Guests \
                can't establish ratings, and the chain button's state has no effect when \
                there is no rating to which to tie \"Opponent Strength\" to"))

    def onSeekButtonClicked(self, button):
        if self.widgets["seek3Radio"].get_active():
            self.__loadSeekEditor(3)
        elif self.widgets["seek2Radio"].get_active():
            self.__loadSeekEditor(2)
        else:
            self.__loadSeekEditor(1)

        minutes, incr, gametype, ratingrange, color, rated, manual = \
            self.__getSeekEditorDialogValues()
        self.connection.glm.seek(minutes, incr, gametype, rated, ratingrange,
                                 color, manual)

    def onSeekAllButtonClicked(self, button):
        for i in range(1, 4):
            self.__loadSeekEditor(i)
            minutes, incr, gametype, ratingrange, color, rated, manual = \
                self.__getSeekEditorDialogValues()
            self.connection.glm.seek(minutes, incr, gametype, rated, ratingrange,
                                     color, manual)

    def onChallengeButtonClicked(self, button, player=None):
        if player is None:
            player = self.lounge.players_tab.getSelectedPlayer()
            if player is None:
                return
        self.challengee = player
        self.in_challenge_mode = True

        for i in range(1, 4):
            self.__loadSeekEditor(i)
            self.__writeSavedSeeks(i)
        self.__updateRatedGameCheck()
        if self.widgets["seek3Radio"].get_active():
            seeknumber = 3
        elif self.widgets["seek2Radio"].get_active():
            seeknumber = 2
        else:
            seeknumber = 1
        self.__updateSeekEditor(seeknumber, challengemode=True)

        self.widgets["challengeeNameLabel"].set_markup(player.getMarkup())
        self.widgets["challengeeImage"].set_from_pixbuf(
            player.getIcon(size=32))
        title = _("Challenge: ") + player.name
        self.widgets["challengeDialog"].set_title(title)
        self.widgets["challengeDialog"].present()

    def onChallengeDialogResponse(self, dialog, response):
        self.widgets["challengeDialog"].hide()
        if response != 5:
            return True

        if self.widgets["challenge3Radio"].get_active():
            self.__loadSeekEditor(3)
        elif self.widgets["challenge2Radio"].get_active():
            self.__loadSeekEditor(2)
        else:
            self.__loadSeekEditor(1)
        minutes, incr, gametype, ratingrange, color, rated, manual = \
            self.__getSeekEditorDialogValues()
        self.connection.om.challenge(self.challengee.name, gametype, minutes, incr,
                                     rated, color)

    def onSeekRadioConfigButtonClicked(self, configimage, seeknumber):
        self.__showSeekEditor(seeknumber)

    def onChallengeRadioConfigButtonClicked(self, configimage, seeknumber):
        self.__showSeekEditor(seeknumber, challengemode=True)

    def onEditSeekDialogResponse(self, dialog, response):
        self.widgets["editSeekDialog"].hide()
        if response != Gtk.ResponseType.OK:
            return
        self.__saveSeekEditor(self.seeknumber)
        self.__writeSavedSeeks(self.seeknumber)

    def __updateSeekEditor(self, seeknumber, challengemode=False):
        self.in_challenge_mode = challengemode
        self.seeknumber = seeknumber
        if not challengemode:
            self.widgets["strengthFrame"].set_sensitive(True)
            self.widgets["strengthFrame"].set_tooltip_text("")
            self.widgets["manualAcceptCheck"].set_sensitive(True)
            self.widgets["manualAcceptCheck"].set_tooltip_text(_(
                "If set you can refuse players accepting your seek"))
        else:
            self.widgets["strengthFrame"].set_sensitive(False)
            self.widgets["strengthFrame"].set_tooltip_text(_(
                "This option is not applicable because you're challenging a player"))
            self.widgets["manualAcceptCheck"].set_sensitive(False)
            self.widgets["manualAcceptCheck"].set_tooltip_text(_(
                "This option is not applicable because you're challenging a player"))

        self.widgets["chainAlignment"].show_all()
        self.__loadSeekEditor(seeknumber)
        self.widgets["seek%dRadio" % seeknumber].set_active(True)
        self.widgets["challenge%dRadio" % seeknumber].set_active(True)

        self.__updateYourRatingHBox()
        self.__updateRatingCenterInfoBox()
        self.__updateToleranceButton()
        self.__updateRatedGameCheck()
        self.onUntimedCheckToggled(self.widgets["untimedCheck"])

        title = _("Edit Seek: ") + self.widgets["seek%dRadio" %
                                                seeknumber].get_label()[:-1]
        self.widgets["editSeekDialog"].set_title(title)

    def __showSeekEditor(self, seeknumber, challengemode=False):
        self.widgets["editSeekDialog"].set_transient_for(self.widgets[
            "fics_lounge"])
        self.__updateSeekEditor(seeknumber, challengemode)
        self.widgets["editSeekDialog"].present()

        # ugly hack to fix https://github.com/pychess/pychess/issues/1024
        # self.widgets["editSeekDialog"].queue_draw() doesn't work
        if sys.platform == "win32":
            self.widgets["editSeekDialog"].hide()
            allocation = self.widgets["editSeekDialog"].get_allocation()
            self.widgets["editSeekDialog"].set_size_request(allocation.width,
                                                            allocation.height)
            self.widgets["editSeekDialog"].show()

    # -------------------------------------------------------- Seek Editor

    def __writeSavedSeeks(self, seeknumber):
        """ Writes saved seek strings for both the Seek Panel and the Challenge Panel """
        minutes, gain, gametype, ratingrange, color, rated, manual = \
            self.__getSeekEditorDialogValues()
        self.savedSeekRadioTexts[seeknumber - 1] = \
            time_control_to_gametype(minutes, gain).display_text
        self.__writeSeekRadioLabels()
        seek = {}

        if gametype == GAME_TYPES["untimed"]:
            seek["time"] = gametype.display_text
        elif gain > 0:
            seek["time"] = _("%(minutes)d min + %(gain)d sec/move") % \
                {'minutes': minutes, 'gain': gain}
        else:
            seek["time"] = _("%d min") % minutes

        if isinstance(gametype, VariantGameType):
            seek["variant"] = "%s" % gametype.display_text

        rrtext = get_rating_range_display_text(ratingrange[0], ratingrange[1])
        if rrtext:
            seek["rating"] = rrtext

        if color == WHITE:
            seek["color"] = _("White")
        elif color == BLACK:
            seek["color"] = _("Black")

        if rated and gametype is not GAME_TYPES["untimed"]:
            seek["rated"] = _("Rated")

        if manual:
            seek["manual"] = _("Manual")

        seek_ = []
        challenge = []
        challengee_is_guest = self.challengee and self.challengee.isGuest()
        for key in ("time", "variant", "rating", "color", "rated", "manual"):
            if key in seek:
                seek_.append(seek[key])
                if key in ("time", "variant", "color") or \
                        (key == "rated" and not challengee_is_guest):
                    challenge.append(seek[key])
        seektext = ", ".join(seek_)
        challengetext = ", ".join(challenge)

        if seeknumber == 1:
            self.widgets["seek1RadioLabel"].set_text(seektext)
            self.widgets["challenge1RadioLabel"].set_text(challengetext)
        elif seeknumber == 2:
            self.widgets["seek2RadioLabel"].set_text(seektext)
            self.widgets["challenge2RadioLabel"].set_text(challengetext)
        else:
            self.widgets["seek3RadioLabel"].set_text(seektext)
            self.widgets["challenge3RadioLabel"].set_text(challengetext)

    def __loadSeekEditor(self, seeknumber):
        self.loading_seek_editor = True
        for widget in self.seekEditorWidgets:
            if widget in self.seekEditorWidgetGettersSetters:
                uistuff.loadDialogWidget(
                    self.widgets[widget],
                    widget,
                    seeknumber,
                    get_value_=self.seekEditorWidgetGettersSetters[widget][0],
                    set_value_=self.seekEditorWidgetGettersSetters[widget][1],
                    first_value=self.seekEditorWidgetDefaults[widget][
                        seeknumber - 1])
            elif widget in self.seekEditorWidgetDefaults:
                uistuff.loadDialogWidget(
                    self.widgets[widget],
                    widget,
                    seeknumber,
                    first_value=self.seekEditorWidgetDefaults[widget][
                        seeknumber - 1])
            else:
                uistuff.loadDialogWidget(self.widgets[widget], widget,
                                         seeknumber)

        self.lastdifference = conf.get("lastdifference-%d" % seeknumber, -1)
        self.loading_seek_editor = False

    def __saveSeekEditor(self, seeknumber):
        for widget in self.seekEditorWidgets:
            if widget in self.seekEditorWidgetGettersSetters:
                uistuff.saveDialogWidget(
                    self.widgets[widget],
                    widget,
                    seeknumber,
                    get_value_=self.seekEditorWidgetGettersSetters[widget][0])
            else:
                uistuff.saveDialogWidget(self.widgets[widget], widget,
                                         seeknumber)

        conf.set("lastdifference-%d" % seeknumber, self.lastdifference)

    def __getSeekEditorDialogValues(self):
        if self.widgets["untimedCheck"].get_active():
            minutes = 0
            incr = 0
        else:
            minutes = int(self.widgets["minutesSpin"].get_value())
            incr = int(self.widgets["gainSpin"].get_value())

        if self.widgets["strengthCheck"].get_active():
            ratingrange = [0, 9999]
        else:
            center = int(self.widgets["ratingCenterSlider"].get_value(
            )) * RATING_SLIDER_STEP
            tolerance = int(self.widgets["toleranceSlider"].get_value(
            )) * RATING_SLIDER_STEP
            minrating = center - tolerance
            minrating = minrating > 0 and minrating or 0
            maxrating = center + tolerance
            maxrating = maxrating >= 3000 and 9999 or maxrating
            ratingrange = [minrating, maxrating]

        if self.widgets["nocolorRadio"].get_active():
            color = None
        elif self.widgets["whitecolorRadio"].get_active():
            color = WHITE
        else:
            color = BLACK

        if self.widgets["noVariantRadio"].get_active() or \
           self.widgets["untimedCheck"].get_active():
            gametype = time_control_to_gametype(minutes, incr)
        else:
            variant_combo_getter = self.seekEditorWidgetGettersSetters[
                "variantCombo"][0]
            variant = variant_combo_getter(self.widgets["variantCombo"])
            gametype = VARIANT_GAME_TYPES[variant]

        rated = self.widgets["ratedGameCheck"].get_active() and not \
            self.widgets["untimedCheck"].get_active()
        manual = self.widgets["manualAcceptCheck"].get_active()

        return minutes, incr, gametype, ratingrange, color, rated, manual

    def __writeSeekRadioLabels(self):
        gameTypes = {_("Untimed"): [0, 1],
                     _("Standard"): [0, 1],
                     _("Blitz"): [0, 1],
                     _("Lightning"): [0, 1]}

        for i in range(3):
            gameTypes[self.savedSeekRadioTexts[i]][0] += 1
        for i in range(3):
            if gameTypes[self.savedSeekRadioTexts[i]][0] > 1:
                labelText = "%s #%d:" % \
                    (self.savedSeekRadioTexts[i], gameTypes[
                     self.savedSeekRadioTexts[i]][1])
                self.widgets["seek%dRadio" % (i + 1)].set_label(labelText)
                self.widgets["challenge%dRadio" % (i + 1)].set_label(labelText)
                gameTypes[self.savedSeekRadioTexts[i]][1] += 1
            else:
                self.widgets["seek%dRadio" % (
                    i + 1)].set_label(self.savedSeekRadioTexts[i] + ":")
                self.widgets["challenge%dRadio" % (
                    i + 1)].set_label(self.savedSeekRadioTexts[i] + ":")

    def __updateRatingRangeBox(self):
        center = int(self.widgets["ratingCenterSlider"].get_value(
        )) * RATING_SLIDER_STEP
        tolerance = int(self.widgets["toleranceSlider"].get_value(
        )) * RATING_SLIDER_STEP
        min_rating = center - tolerance
        min_rating = min_rating > 0 and min_rating or 0
        max_rating = center + tolerance
        max_rating = max_rating >= 3000 and 9999 or max_rating

        self.widgets["ratingRangeMinLabel"].set_label("%d" % min_rating)
        self.widgets["ratingRangeMaxLabel"].set_label("%d" % max_rating)

        for widgetName, rating in (("ratingRangeMinImage", min_rating),
                                   ("ratingRangeMaxImage", max_rating)):
            pixbuf = FICSPlayer.getIconByRating(rating)
            self.widgets[widgetName].set_from_pixbuf(pixbuf)

        self.widgets["ratingRangeMinImage"].show()
        self.widgets["ratingRangeMinLabel"].show()
        self.widgets["dashLabel"].show()
        self.widgets["ratingRangeMaxImage"].show()
        self.widgets["ratingRangeMaxLabel"].show()
        if min_rating == 0:
            self.widgets["ratingRangeMinImage"].hide()
            self.widgets["ratingRangeMinLabel"].hide()
            self.widgets["dashLabel"].hide()
            self.widgets["ratingRangeMaxLabel"].set_label("%d↓" % max_rating)
        if max_rating == 9999:
            self.widgets["ratingRangeMaxImage"].hide()
            self.widgets["ratingRangeMaxLabel"].hide()
            self.widgets["dashLabel"].hide()
            self.widgets["ratingRangeMinLabel"].set_label("%d↑" % min_rating)
        if min_rating == 0 and max_rating == 9999:
            self.widgets["ratingRangeMinLabel"].set_label(_("Any strength"))
            self.widgets["ratingRangeMinLabel"].show()

    def __getGameType(self):
        if self.widgets["untimedCheck"].get_active():
            gametype = GAME_TYPES["untimed"]
        elif self.widgets["noVariantRadio"].get_active():
            minutes = int(self.widgets["minutesSpin"].get_value())
            gain = int(self.widgets["gainSpin"].get_value())
            gametype = time_control_to_gametype(minutes, gain)
        else:
            variant_combo_getter = self.seekEditorWidgetGettersSetters[
                "variantCombo"][0]
            variant = variant_combo_getter(self.widgets["variantCombo"])
            gametype = VARIANT_GAME_TYPES[variant]
        return gametype

    def __updateYourRatingHBox(self):
        gametype = self.__getGameType()
        self.widgets["yourRatingNameLabel"].set_label(
            "(" + gametype.display_text + ")")
        rating = self.__getRating(gametype.rating_type)
        if rating is None:
            self.widgets["yourRatingImage"].clear()
            self.widgets["yourRatingLabel"].set_label(_("Unrated"))
            return
        pixbuf = FICSPlayer.getIconByRating(rating)
        self.widgets["yourRatingImage"].set_from_pixbuf(pixbuf)
        self.widgets["yourRatingLabel"].set_label(str(rating))

        center = int(self.widgets["ratingCenterSlider"].get_value(
        )) * RATING_SLIDER_STEP
        rating = self.__clamp(rating)
        difference = rating - center
        if self.loading_seek_editor is False and self.chainbox.active and \
                difference != self.lastdifference:
            newcenter = rating - self.lastdifference
            self.widgets["ratingCenterSlider"].set_value(newcenter //
                                                         RATING_SLIDER_STEP)
        else:
            self.lastdifference = difference

    def __clamp(self, rating):
        assert isinstance(rating, int)
        mod = rating % RATING_SLIDER_STEP
        if mod > RATING_SLIDER_STEP // 2:
            return rating - mod + RATING_SLIDER_STEP
        else:
            return rating - mod

    def __updateRatedGameCheck(self):
        # on FICS, untimed games can't be rated, nor can games against a guest
        if not self.connection.isRegistred():
            self.widgets["ratedGameCheck"].set_active(False)
            sensitive = False
            self.widgets["ratedGameCheck"].set_tooltip_text(_(
                "You can't play rated games because you are logged in as a guest"))
        elif self.widgets["untimedCheck"].get_active():
            sensitive = False
            self.widgets["ratedGameCheck"].set_tooltip_text(
                _("You can't play rated games because \"Untimed\" is checked, ") +
                _("and on FICS, untimed games can't be rated"))
        elif self.in_challenge_mode and self.challengee.isGuest():
            sensitive = False
            self.widgets["ratedGameCheck"].set_tooltip_text(
                _("This option is not available because you're challenging a guest, ") +
                _("and guests can't play rated games"))
        else:
            sensitive = True
            self.widgets["ratedGameCheck"].set_tooltip_text("")
        self.widgets["ratedGameCheck"].set_sensitive(sensitive)

    def __initVariantCombo(self, combo):
        model = Gtk.TreeStore(str)
        cellRenderer = Gtk.CellRendererText()
        combo.clear()
        combo.pack_start(cellRenderer, True)
        combo.add_attribute(cellRenderer, 'text', 0)
        combo.set_model(model)

        groupNames = {VARIANTS_SHUFFLE: _("Shuffle"),
                      VARIANTS_OTHER: _("Other (standard rules)"),
                      VARIANTS_OTHER_NONSTANDARD:
                      _("Other (non standard rules)"), }
        ficsvariants = [
            v
            for k, v in variants.items()
            if k in VARIANT_GAME_TYPES and v.variant not in UNSUPPORTED
        ]
        groups = groupby(ficsvariants, attrgetter("variant_group"))
        pathToVariant = {}
        variantToPath = {}
        for i, (id, group) in enumerate(groups):
            sel_iter = model.append(None, (groupNames[id], ))
            for variant in group:
                subiter = model.append(sel_iter, (variant.name, ))
                path = model.get_path(subiter)
                path = path.to_string()
                pathToVariant[path] = variant.variant
                variantToPath[variant.variant] = path

        # this stops group names (eg "Shuffle") from being displayed in
        # submenus
        def cellFunc(combo, cell, model, sel_iter, data):
            isChildNode = not model.iter_has_child(sel_iter)
            cell.set_property("sensitive", isChildNode)

        combo.set_cell_data_func(cellRenderer, cellFunc, None)

        def comboGetter(combo):
            path = model.get_path(combo.get_active_iter())
            path = path.to_string()
            return pathToVariant[path]

        def comboSetter(combo, variant):
            if variant not in VARIANT_GAME_TYPES:
                variant = LOSERSCHESS
            combo.set_active_iter(model.get_iter(variantToPath[variant]))

        return comboGetter, comboSetter

    def __getRating(self, gametype):
        if self.finger is None:
            return None
        try:
            rating = self.finger.getRating(type=gametype)
        except KeyError:  # the user doesn't have a rating for this game type
            rating = None
        return rating

    @idle_add
    def onFinger(self, fm, finger):
        if not finger.getName() == self.connection.getUsername():
            return
        self.finger = finger

        numfingers = conf.get("numberOfFingers", 0) + 1
        conf.set("numberOfFingers", numfingers)
        if conf.get("numberOfTimesLoggedInAsRegisteredUser",
                    0) is 1 and numfingers is 1:
            standard = self.__getRating(TYPE_STANDARD)
            blitz = self.__getRating(TYPE_BLITZ)
            lightning = self.__getRating(TYPE_LIGHTNING)

            if standard is not None:
                self.seekEditorWidgetDefaults["ratingCenterSlider"][
                    0] = standard // RATING_SLIDER_STEP
            elif blitz is not None:
                self.seekEditorWidgetDefaults["ratingCenterSlider"][
                    0] = blitz // RATING_SLIDER_STEP
            if blitz is not None:
                self.seekEditorWidgetDefaults["ratingCenterSlider"][
                    1] = blitz // RATING_SLIDER_STEP
            if lightning is not None:
                self.seekEditorWidgetDefaults["ratingCenterSlider"][
                    2] = lightning // RATING_SLIDER_STEP
            elif blitz is not None:
                self.seekEditorWidgetDefaults["ratingCenterSlider"][
                    2] = blitz // RATING_SLIDER_STEP

            for i in range(1, 4):
                self.__loadSeekEditor(i)
                self.__updateSeekEditor(i)
                self.__saveSeekEditor(i)
                self.__writeSavedSeeks(i)

        self.__updateYourRatingHBox()

    def onTimeSpinChanged(self, spin):
        minutes = self.widgets["minutesSpin"].get_value_as_int()
        gain = self.widgets["gainSpin"].get_value_as_int()
        name = time_control_to_gametype(minutes, gain).display_text
        self.widgets["timeControlNameLabel"].set_label("%s" % name)
        self.__updateYourRatingHBox()

    def onUntimedCheckToggled(self, check):
        is_untimed_game = check.get_active()
        self.widgets["timeControlConfigVBox"].set_sensitive(
            not is_untimed_game)
        # on FICS, untimed games can't be rated and can't be a chess variant
        self.widgets["variantFrame"].set_sensitive(not is_untimed_game)
        if is_untimed_game:
            self.widgets["variantFrame"].set_tooltip_text(
                _("You can't select a variant because \"Untimed\" is checked, ") +
                _("and on FICS, untimed games have to be normal chess rules"))
        else:
            self.widgets["variantFrame"].set_tooltip_text("")
        self.__updateRatedGameCheck(
        )  # sets sensitivity of widgets["ratedGameCheck"]
        self.__updateYourRatingHBox()

    def onStrengthCheckToggled(self, check):
        strengthsensitive = not check.get_active()
        self.widgets["strengthConfigVBox"].set_sensitive(strengthsensitive)

    def onRatingCenterSliderChanged(self, slider):
        center = int(self.widgets["ratingCenterSlider"].get_value(
        )) * RATING_SLIDER_STEP
        pixbuf = FICSPlayer.getIconByRating(center)
        self.widgets["ratingCenterLabel"].set_label("%d" % (center))
        self.widgets["ratingCenterImage"].set_from_pixbuf(pixbuf)
        self.__updateRatingRangeBox()

        rating = self.__getRating(self.__getGameType().rating_type)
        if rating is None:
            return
        rating = self.__clamp(rating)
        self.lastdifference = rating - center

    def __updateRatingCenterInfoBox(self):
        if self.widgets["toleranceHBox"].get_property("visible") is True:
            self.widgets["ratingCenterInfoHBox"].show()
        else:
            self.widgets["ratingCenterInfoHBox"].hide()

    def __updateToleranceButton(self):
        if self.widgets["toleranceHBox"].get_property("visible") is True:
            self.widgets["toleranceButton"].set_property("label", _("Hide"))
        else:
            self.widgets["toleranceButton"].set_property("label",
                                                         _("Change Tolerance"))

    def onToleranceButtonClicked(self, button):
        if self.widgets["toleranceHBox"].get_property("visible") is True:
            self.widgets["toleranceHBox"].hide()
        else:
            self.widgets["toleranceHBox"].show()
        self.__updateToleranceButton()
        self.__updateRatingCenterInfoBox()

    def onToleranceSliderChanged(self, slider):
        tolerance = int(self.widgets["toleranceSlider"].get_value(
        )) * RATING_SLIDER_STEP
        self.widgets["toleranceLabel"].set_label("±%d" % tolerance)
        self.__updateRatingRangeBox()

    def onColorRadioChanged(self, radio):
        if self.widgets["nocolorRadio"].get_active():
            self.widgets["colorImage"].set_from_file(addDataPrefix(
                "glade/piece-unknown.png"))
            self.widgets["colorImage"].set_sensitive(False)
        elif self.widgets["whitecolorRadio"].get_active():
            self.widgets["colorImage"].set_from_file(addDataPrefix(
                "glade/piece-white.png"))
            self.widgets["colorImage"].set_sensitive(True)
        elif self.widgets["blackcolorRadio"].get_active():
            self.widgets["colorImage"].set_from_file(addDataPrefix(
                "glade/piece-black.png"))
            self.widgets["colorImage"].set_sensitive(True)

    def onVariantRadioChanged(self, radio):
        self.__updateYourRatingHBox()

    def onVariantComboChanged(self, combo):
        self.widgets["variantRadio"].set_active(True)
        self.__updateYourRatingHBox()
        min, gain, gametype, ratingrange, color, rated, manual = \
            self.__getSeekEditorDialogValues()
        self.widgets["variantCombo"].set_tooltip_text(variants[
            gametype.variant_type].__desc__)

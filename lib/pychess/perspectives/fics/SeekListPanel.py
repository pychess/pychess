from gi.repository import Gtk, Gdk, GdkPixbuf

from pychess.ic.FICSObjects import FICSSoughtMatch, FICSChallenge, \
    get_seek_tooltip_text, get_challenge_tooltip_text
from pychess.ic import TYPE_BLITZ, TYPE_LIGHTNING, TYPE_STANDARD, RATING_TYPES, \
    TYPE_BULLET, TYPE_ONE_MINUTE, TYPE_THREE_MINUTE, TYPE_FIVE_MINUTE, \
    TYPE_FIFTEEN_MINUTE, TYPE_FORTYFIVE_MINUTE, \
    get_infobarmessage_content
from pychess.perspectives.fics.ParrentListSection import ParrentListSection, cmp, \
    SEPARATOR, ACCEPT, ASSESS, FOLLOW, CHAT, CHALLENGE, FINGER, ARCHIVED
from pychess.Utils.IconLoader import get_pixbuf
from pychess.System import conf, uistuff
from pychess.System.Log import log
from pychess.System.prefix import addDataPrefix
from pychess.widgets import mainwindow
from pychess.widgets.preferencesDialog import SoundTab
from pychess.widgets.InfoBar import InfoBarMessage, InfoBarMessageButton

__title__ = _("Seeks / Challenges")

__icon__ = addDataPrefix("glade/manseek.svg")

__desc__ = _("Handle seeks and challenges")


class Sidepanel(ParrentListSection):

    def load(self, widgets, connection, lounge):
        self.widgets = widgets
        self.connection = connection
        self.lounge = lounge
        self.infobar = lounge.infobar

        __widget__ = lounge.seek_list

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

        self.seek_filter = self.store.filter_new()
        self.seek_filter.set_visible_func(self.seek_filter_func)

        self.filter_toggles = {}
        self.filter_buttons = ("standard_toggle1", "blitz_toggle1", "lightning_toggle1", "variant_toggle1", "computer_toggle1")
        for widget in self.filter_buttons:
            uistuff.keep(self.widgets[widget], widget)
            self.widgets[widget].connect("toggled", self.on_filter_button_toggled)
            initial = conf.get(widget)
            self.filter_toggles[widget] = initial
            self.widgets[widget].set_active(initial)

        self.model = self.seek_filter.sort_new_with_model()
        self.tv.set_model(self.model)

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

        return __widget__

    def seek_filter_func(self, model, iter, data):
        sought_match = model[iter][0]
        is_computer = sought_match.player.isComputer()
        is_standard = sought_match.game_type.rating_type in (TYPE_STANDARD, TYPE_FIFTEEN_MINUTE, TYPE_FORTYFIVE_MINUTE) and not is_computer
        is_blitz = sought_match.game_type.rating_type in (TYPE_BLITZ, TYPE_THREE_MINUTE, TYPE_FIVE_MINUTE) and not is_computer
        is_lightning = sought_match.game_type.rating_type in (TYPE_LIGHTNING, TYPE_BULLET, TYPE_ONE_MINUTE) and not is_computer
        is_variant = sought_match.game_type.rating_type in RATING_TYPES[9:] and not is_computer
        return (
            self.filter_toggles["computer_toggle1"] and is_computer) or (
            self.filter_toggles["standard_toggle1"] and is_standard) or (
            self.filter_toggles["blitz_toggle1"] and is_blitz) or (
            self.filter_toggles["lightning_toggle1"] and is_lightning) or (
            self.filter_toggles["variant_toggle1"] and is_variant)

    def on_filter_button_toggled(self, widget):
        for button in self.filter_buttons:
            self.filter_toggles[button] = self.widgets[button].get_active()
        self.seek_filter.refilter()

    def onAssessReceived(self, glm, assess):
        if self.assess_sent:
            self.assess_sent = False
            dialog = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.INFO,
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
            grid.attach(Gtk.Label(label=""), 0, 0, 1, 1)
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
        elif column == 7:
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

    def onPlayingGame(self, bm, game):
        self._clear_messages()
        self.widgets["seekListContent"].set_sensitive(False)
        self.widgets["clearSeeksButton"].set_sensitive(False)
        self.__updateActiveSeeksLabel()

    def onCurGameEnded(self, bm, game):
        self.widgets["seekListContent"].set_sensitive(True)

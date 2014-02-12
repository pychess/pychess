# -*- coding: utf-8 -*-

import Queue
from StringIO import StringIO
from time import strftime, localtime, time
from math import e
from operator import attrgetter
from itertools import groupby

import gtk, gobject, pango, re
from gtk.gdk import pixbuf_new_from_file
from gobject import GObject, SIGNAL_RUN_FIRST

from pychess.ic import *
from pychess.System import conf, glock, uistuff
from pychess.System.GtkWorker import Publisher
from pychess.System.prefix import addDataPrefix
from pychess.System.ping import Pinger
from pychess.System.Log import log
from pychess.widgets import ionest
from pychess.widgets import gamewidget
from pychess.widgets.ChatWindow import ChatWindow
from pychess.widgets.ConsoleWindow import ConsoleWindow
from pychess.widgets.SpotGraph import SpotGraph
from pychess.widgets.ChainVBox import ChainVBox
from pychess.widgets.preferencesDialog import SoundTab
from pychess.widgets.InfoBar import *
from pychess.Utils.const import *
from pychess.Utils.GameModel import GameModel
from pychess.Utils.IconLoader import load_icon
from pychess.Utils.TimeModel import TimeModel
from pychess.Players.ICPlayer import ICPlayer
from pychess.Players.Human import Human
from pychess.Savers import pgn, fen
from pychess.Variants import variants
from pychess.Variants.normal import NormalChess

from FICSObjects import *
from ICGameModel import ICGameModel
from pychess.Utils.Rating import Rating

class ICLounge (GObject):
    __gsignals__ = {
        'logout'        : (SIGNAL_RUN_FIRST, None, ()),
        'autoLogout'    : (SIGNAL_RUN_FIRST, None, ()),
    }
    
    def __init__ (self, connection, helperconn, host):
        GObject.__init__(self)
        self.connection = connection
        self.helperconn = helperconn
        self.host = host
        
        self.need_who = True
        self.need_games = True
        
        self.widgets = uistuff.GladeWidgets("fics_lounge.glade")
        uistuff.keepWindowSize("fics_lounge", self.widgets["fics_lounge"])
        self.infobar = InfoBar()
        self.infobar.hide()
        self.widgets["fics_lounge_infobar_vbox"].pack_start(self.infobar,
            expand=False, fill=False)

        def on_window_delete (window, event):
            self.close()
            self.emit("logout")
            return True
        self.widgets["fics_lounge"].connect("delete-event", on_window_delete)

        def on_logoffButton_clicked (button):
            self.close()
            self.emit("logout")
        self.widgets["logoffButton"].connect("clicked", on_logoffButton_clicked)        

        def on_autoLogout (alm):
            self.close()
            self.emit("autoLogout")
        self.connection.alm.connect("logOut", on_autoLogout)

        self.connection.connect("disconnected", lambda connection: self.close())
        self.connection.connect("error", self.on_connection_error)
        
        # workaround for https://code.google.com/p/pychess/issues/detail?id=677
        self.connection.nm.connect("readNews", self.on_news_item)
        
        if self.connection.isRegistred():
            numtimes = conf.get("numberOfTimesLoggedInAsRegisteredUser", 0) + 1
            conf.set("numberOfTimesLoggedInAsRegisteredUser", numtimes)

        global sections
        sections = (
            VariousSection(self.widgets, self.connection),
            UserInfoSection(self.widgets, self.connection, self.host),
            NewsSection(self.widgets, self.connection),

            SeekTabSection(self.widgets, self.connection, self.infobar),
            SeekGraphSection(self.widgets, self.connection),
            PlayerTabSection(self.widgets, self.connection),
            GameTabSection(self.widgets, self.connection),
            AdjournedTabSection(self.widgets, self.connection, self.infobar),

            ChatWindow(self.widgets, self.connection),
            ConsoleWindow(self.widgets, self.connection),

            SeekChallengeSection(self.widgets, self.connection),
            
            # This is not really a section. It handles server messages which
            # don't correspond to a running game
            Messages(self.widgets, self.connection, self.infobar),
            
            # This is not really a section. Merely a pair of BoardManager connects
            # which takes care of ionest and stuff when a new game is started or
            # observed
            CreatedBoards(self.widgets, self.connection)
        )

    @glock.glocked
    def on_news_item (self, nm, news):            
        self.widgets["show_chat_button"].set_sensitive(True)    

    def show (self):
        self.widgets["fics_lounge"].show()

    def present (self):
        self.widgets["fics_lounge"].present()
    
    def on_connection_error (self, connection, error):
        log.warning("ICLounge.on_connection_error: %s" % repr(error))
        self.close()
    
    @glock.glocked
    def close (self):
        if self.widgets != None:
            self.widgets["fics_lounge"].hide()
        global sections
        if 'sections' in globals() and sections != None:
            for i in range(len(sections)):
                if hasattr(sections[i], "__del__"):
                    sections[i].__del__()
        sections = None
        self.widgets = None

################################################################################
# Initialize Sections                                                          #
################################################################################

class Section (object):
    def get_infobarmessage_content (self, player, text, gametype=None):
        content = gtk.HBox()
        icon = gtk.Image()
        icon.set_from_pixbuf(player.getIcon(size=32, gametype=gametype))
        content.pack_start(icon, expand=False, fill=False, padding=4)
        label = gtk.Label()
        label.set_markup(player.getMarkup(gametype=gametype))
        content.pack_start(label, expand=False, fill=False)
        label = gtk.Label()
        label.set_markup(text)
        content.pack_start(label, expand=False, fill=False)
        
        return content
    
############################################################################
# Initialize Various smaller sections                                      #
############################################################################

class VariousSection(Section):
    def __init__ (self, widgets, connection):
        #sizeGroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        #sizeGroup.add_widget(widgets["show_chat_label"])
        #sizeGroup.add_widget(widgets["show_console_label"])
        #sizeGroup.add_widget(widgets["log_off_label"])

        #widgets["show_console_button"].hide()

        connection.em.connect("onCommandNotFound", lambda em, cmd:
                log.error("Fics answered '%s': Command not found" % cmd))

############################################################################
# Initialize User Information Section                                      #
############################################################################

class UserInfoSection(Section):

    def __init__ (self, widgets, connection, host):
        self.widgets = widgets
        self.connection = connection
        self.host = host
        self.pinger = None
        self.ping_label = None

        self.dock = self.widgets["fingerTableDock"]

        self.connection.fm.connect("fingeringFinished", self.onFinger)
        self.connection.fm.finger(self.connection.getUsername())
        self.connection.bm.connect("curGameEnded", lambda *args:
                self.connection.fm.finger(self.connection.getUsername()))

        self.widgets["usernameLabel"].set_markup(
                "<b>%s</b>" % self.connection.getUsername())

    def __del__ (self):
        if self.pinger != None:
            self.pinger.stop()

    def onFinger (self, fm, finger):
        if finger.getName().lower() != self.connection.getUsername().lower():
            print finger.getName(), self.connection.getUsername()
            return
        glock.acquire()
        try:
            rows = 1
            if finger.getRating(): rows += len(finger.getRating())+1
            if finger.getEmail(): rows += 1
            if finger.getCreated(): rows += 1

            table = gtk.Table(6, rows)
            table.props.column_spacing = 12
            table.props.row_spacing = 4

            def label(value, xalign=0, is_error=False):
                if type(value) == float:
                    value = str(int(value))
                if is_error:
                    label = gtk.Label()
                    label.set_markup('<span size="larger" foreground="red">' + value + "</span>")
                else:
                    label = gtk.Label(value)
                label.props.xalign = xalign
                return label

            row = 0

            if finger.getRating():
                for i, item in enumerate((_("Rating"), _("Win"), _("Draw"), _("Loss"))):
                    table.attach(label(item, xalign=1), i+1,i+2,0,1)
                row += 1

                for rating_type, rating in finger.getRating().iteritems():
                    ratinglabel = label( \
                        GAME_TYPES_BY_RATING_TYPE[rating_type].display_text + ":")
                    table.attach(ratinglabel, 0, 1, row, row+1)
                    if rating_type is TYPE_WILD:
                        ratinglabel.set_tooltip_text(
                        _("On FICS, your \"Wild\" rating encompasses all of the following variants at all time controls:\n") +
                        ", ".join([gt.display_text for gt in WildGameType.instances()]))
                    table.attach(label(rating.elo, xalign=1), 1, 2, row, row+1)
                    table.attach(label(rating.wins, xalign=1), 2, 3, row, row+1)
                    table.attach(label(rating.draws, xalign=1), 3, 4, row, row+1)
                    table.attach(label(rating.losses, xalign=1), 4, 5, row, row+1)
                    row += 1

                table.attach(gtk.HSeparator(), 0, 6, row, row+1, ypadding=2)
                row += 1
            
            if finger.getSanctions() != "":
                table.attach(label(_("Sanctions")+":", is_error=True), 0, 1, row, row+1)
                table.attach(label(finger.getSanctions()), 1, 6, row, row+1)
                row += 1
            
            if finger.getEmail():
                table.attach(label(_("Email")+":"), 0, 1, row, row+1)
                table.attach(label(finger.getEmail()), 1, 6, row, row+1)
                row += 1
            
            if finger.getCreated():
                table.attach(label(_("Spent")+":"), 0, 1, row, row+1)
                s = strftime("%Y %B %d ", localtime(time()))
                s += _("online in total")
                table.attach(label(s), 1, 6, row, row+1)
                row += 1

            table.attach(label(_("Ping")+":"), 0, 1, row, row+1)
            if self.ping_label:
                if self.dock.get_children():
                    self.dock.get_children()[0].remove(self.ping_label)
            else:
                self.ping_label = gtk.Label(_("Connecting")+"...")
                self.ping_label.props.xalign = 0
            def callback (pinger, pingtime):
                if type(pingtime) == str:
                    self.ping_label.set_text(pingtime)
                elif pingtime == -1:
                    self.ping_label.set_text(_("Unknown"))
                else: self.ping_label.set_text("%.0f ms" % pingtime)
            if not self.pinger:
                self.pinger = Pinger(self.host)
                self.pinger.start()
                self.pinger.connect("recieved", callback)
                self.pinger.connect("error", callback)
            table.attach(self.ping_label, 1, 6, row, row+1)
            row += 1

            if not self.connection.isRegistred():
                vbox = gtk.VBox()
                table.attach(vbox, 0, 6, row, row+1)
                label0 = gtk.Label(_("You are currently logged in as a guest.\nA guest is not able to play rated games, and thus the offer of games will be smaller."))
                label0.props.xalign = 0
                label0.props.wrap = True
                label0.props.width_request = 300
                vbox.add(label0)
                eventbox = uistuff.LinkLabel(_("Register now"),
                        "http://www.freechess.org/Register/index.html")
                vbox.add(eventbox)

            if self.dock.get_children():
                self.dock.remove(self.dock.get_children()[0])
            self.dock.add(table)
            self.dock.show_all()
        finally:
            glock.release()

############################################################################
# Initialize News Section                                                  #
############################################################################

class NewsSection(Section):

    def __init__(self, widgets, connection):
        self.widgets = widgets
        connection.nm.connect("readNews", self.onNewsItem)

    def onNewsItem (self, nm, news):
        glock.acquire()
        try:
            weekday, month, day, title, details = news

            dtitle = "%s, %s %s: %s" % (weekday, month, day, title)
            label = gtk.Label(dtitle)
            label.props.width_request = 300
            label.props.xalign = 0
            label.set_ellipsize(pango.ELLIPSIZE_END)
            expander = gtk.Expander()
            expander.set_label_widget(label)
            expander.set_tooltip_text(title)
            textview = gtk.TextView ()
            textview.set_wrap_mode (gtk.WRAP_WORD)
            textview.set_editable (False)
            textview.set_cursor_visible (False)
            textview.props.pixels_above_lines = 4
            textview.props.pixels_below_lines = 4
            textview.props.right_margin = 2
            textview.props.left_margin = 6
            uistuff.initTexviewLinks(textview, details)

            alignment = gtk.Alignment()
            alignment.set_padding(3, 6, 12, 0)
            alignment.props.xscale = 1
            alignment.add(textview)

            expander.add(alignment)
            expander.show_all()
            self.widgets["newsVBox"].pack_end(expander)
        finally:
            glock.release()

############################################################################
# Initialize Lists                                                         #
############################################################################

class ParrentListSection (Section):
    """ Parrent for sections mainly consisting of a large treeview """
    def __init__ (self):
        def updateLists (queuedCalls):
            for task in queuedCalls:
                func = task[0]
                func(*task[1:])
        self.listPublisher = Publisher(updateLists, Publisher.SEND_LIST)
        self.listPublisher.start()

    def addColumns (self, treeview, *columns, **keyargs):
        if "hide" in keyargs: hide = keyargs["hide"]
        else: hide = []
        if "pix" in keyargs: pix = keyargs["pix"]
        else: pix = []
        for i, name in enumerate(columns):
            if i in hide: continue
            if i in pix:
                crp = gtk.CellRendererPixbuf()
                crp.props.xalign = .5
                column = gtk.TreeViewColumn(name, crp, pixbuf=i)
            else:
                crt = gtk.CellRendererText()
                column = gtk.TreeViewColumn(name, crt, text=i)
                column.set_sort_column_id(i)
                column.set_resizable(True)

            column.set_reorderable(True)
            treeview.append_column(column)

    def lowLeftSearchPosFunc (self, tv, search_dialog):
        x = tv.allocation.x + tv.get_toplevel().window.get_position()[0]
        y = tv.allocation.y + tv.get_toplevel().window.get_position()[1] + \
            tv.allocation.height
        search_dialog.move(x, y)
        search_dialog.show_all()

    def pixCompareFunction (self, treemodel, iter0, iter1, column):
        pix0 = treemodel.get_value(iter0, column)
        pix1 = treemodel.get_value(iter1, column)
        if type(pix0) == gtk.gdk.Pixbuf and type(pix1) == gtk.gdk.Pixbuf:
            return cmp(pix0.get_pixels(), pix1.get_pixels())
        return cmp(pix0, pix1)
    
    def timeCompareFunction (self, treemodel, iter0, iter1, column):
        (minute0, minute1) = (treemodel.get_value(iter0, 7), treemodel.get_value(iter1, 7))
        return cmp(minute0, minute1)



########################################################################
# Initialize Seek List                                                 #
########################################################################

class SeekTabSection (ParrentListSection):

    def __init__ (self, widgets, connection, infobar):
        ParrentListSection.__init__(self)

        self.widgets = widgets
        self.connection = connection
        self.infobar = infobar
        self.messages = {}
        self.seeks = {}
        self.challenges = {}
        self.seekPix = pixbuf_new_from_file(addDataPrefix("glade/seek.png"))
        self.chaPix = pixbuf_new_from_file(addDataPrefix("glade/challenge.png"))
        self.manSeekPix = pixbuf_new_from_file(addDataPrefix("glade/manseek.png"))
        
        self.tv = self.widgets["seektreeview"]
        self.store = gtk.ListStore(FICSSoughtMatch, gtk.gdk.Pixbuf,
            gtk.gdk.Pixbuf, str, int, str, str, str, int, str, str)
        self.tv.set_model(gtk.TreeModelSort(self.store))
        self.addColumns (self.tv, "FICSSoughtMatch", "", "", _("Name"),
            _("Rating"), _("Rated"), _("Type"), _("Clock"), "gametime",
            "textcolor", "tooltip", hide=[0,8,9,10], pix=[1,2] )
        self.tv.set_search_column(3)
        self.tv.set_tooltip_column(10,)
        for i in range(2, 8):
            self.tv.get_model().set_sort_func(i, self.compareFunction, i)
        try:
            self.tv.set_search_position_func(self.lowLeftSearchPosFunc)
        except AttributeError:
            # Unknow signal name is raised by gtk < 2.10
            pass
        for n in range(2, 7):
            column = self.tv.get_column(n)
            for cellrenderer in column.get_cell_renderers():
                column.add_attribute(cellrenderer, "foreground", 9)
        self.selection = self.tv.get_selection()
        self.lastSeekSelected = None
        self.selection.set_select_function(self.selectFunction, full=True)
        self.selection.connect("changed", self.onSelectionChanged)
        self.widgets["clearSeeksButton"].connect("clicked", self.onClearSeeksClicked)
        self.widgets["acceptButton"].connect("clicked", self.onAcceptClicked)
        self.widgets["declineButton"].connect("clicked", self.onDeclineClicked)
        self.tv.connect("row-activated", self.row_activated)
        
        self.connection.seeks.connect("FICSSeekCreated", lambda seeks, seek:
                self.listPublisher.put((self.onAddSeek, seek)))
        self.connection.seeks.connect("FICSSeekRemoved", lambda seeks, seek:
                self.listPublisher.put((self.onRemoveSeek, seek)))
        self.connection.challenges.connect("FICSChallengeIssued",
            lambda challenges, challenge: \
            self.listPublisher.put((self.onChallengeAdd, challenge)))
        self.connection.challenges.connect("FICSChallengeRemoved",
            lambda challenges, challenge: \
            self.listPublisher.put((self.onChallengeRemove, challenge)))
        self.connection.glm.connect("our-seeks-removed", lambda glm:
                self.listPublisher.put((self.our_seeks_removed,)))
        self.connection.bm.connect("playGameCreated", lambda bm, game:
                self.listPublisher.put((self.onPlayingGame,)) )
        self.connection.bm.connect("curGameEnded", lambda bm, game:
                self.listPublisher.put((self.onCurGameEnded,)) )
        
    def selectFunction (self, selection, model, path, is_selected):
        if model[path][9] == "grey": return False
        else: return True
    
    def __isAChallengeOrOurSeek (self, row):
        sought = row[0]
        textcolor = row[9]
        if (isinstance(sought, FICSChallenge)) or (textcolor == "grey"):
            return True
        else:
            return False
    
    def compareFunction (self, model, iter0, iter1, column):
        row0 = list(model[model.get_path(iter0)])
        row1 = list(model[model.get_path(iter1)])
        is_ascending = True if self.tv.get_column(column-1).get_sort_order() is \
                               gtk.SORT_ASCENDING else False
        if self.__isAChallengeOrOurSeek(row0) and not self.__isAChallengeOrOurSeek(row1):
            if is_ascending: return -1
            else: return 1
        elif self.__isAChallengeOrOurSeek(row1) and not self.__isAChallengeOrOurSeek(row0):
            if is_ascending: return 1
            else: return -1
        elif column is 7:
            return self.timeCompareFunction(model, iter0, iter1, column)
        else:
            value0 = row0[column]
            value0 = value0.lower() if isinstance(value0, str) else value0
            value1 = row1[column]
            value1 = value1.lower() if isinstance(value1, str) else value1
            return cmp(value0, value1)

    def __updateActiveSeeksLabel (self):
        count = len(self.seeks) + len(self.challenges)
        self.widgets["activeSeeksLabel"].set_text(_("Active seeks: %d") % count)
    
    def onAddSeek (self, seek):
        pix = self.seekPix if seek.automatic else self.manSeekPix
        textcolor = "grey" if seek.player.name == self.connection.getUsername() \
            else "black"
        seek_ = [seek, seek.player.getIcon(gametype=seek.game_type), pix,
            seek.player.name + seek.player.display_titles(),
            seek.player.getRating(seek.game_type.rating_type).elo,
            seek.display_rated, seek.game_type.display_text,
            seek.display_timecontrol, seek.sortable_time, textcolor,
            get_seek_tooltip_text(seek)]
 
        if textcolor == "grey":
            ti = self.store.prepend(seek_)
            self.tv.scroll_to_cell(self.store.get_path(ti))
            self.widgets["clearSeeksButton"].set_sensitive(True)
        else:
            ti = self.store.append(seek_)
        self.seeks[hash(seek)] = ti
        self.__updateActiveSeeksLabel()
        
    def onRemoveSeek (self, seek):
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
    
    def onChallengeAdd (self, challenge):
        log.debug("onChallengeAdd: %s" % challenge)
        SoundTab.playAction("aPlayerChecks")
        
        # TODO: differentiate between challenges and manual-seek-accepts
        # (wait until seeks are comparable FICSSeek objects to do this)
        # Related: http://code.google.com/p/pychess/issues/detail?id=206
        if challenge.adjourned:
            text = _(" would like to resume your adjourned <b>%(time)s</b> " + \
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
        content = self.get_infobarmessage_content(challenge.player, text,
                                                  gametype=challenge.game_type)
        def callback (infobar, response, message):
            if response == gtk.RESPONSE_ACCEPT:
                self.connection.om.acceptIndex(challenge.index)
            elif response == gtk.RESPONSE_NO:
                self.connection.om.declineIndex(challenge.index)
            message.dismiss()
            return False
        message = InfoBarMessage(gtk.MESSAGE_QUESTION, content, callback)
        message.add_button(InfoBarMessageButton(_("Accept"), gtk.RESPONSE_ACCEPT))
        message.add_button(InfoBarMessageButton(_("Decline"), gtk.RESPONSE_NO))
        message.add_button(InfoBarMessageButton(gtk.STOCK_CLOSE, gtk.RESPONSE_CANCEL))
        self.messages[hash(challenge)] = message
        self.infobar.push_message(message)
        
        ti = self.store.prepend ([challenge,
            challenge.player.getIcon(gametype=challenge.game_type),
            self.chaPix, challenge.player.name + challenge.player.display_titles(),
            challenge.player.getRating(challenge.game_type.rating_type).elo,
            challenge.display_rated, challenge.game_type.display_text,
            challenge.display_timecontrol, challenge.sortable_time, "black",
            get_challenge_tooltip_text(challenge)])
        self.challenges[hash(challenge)] = ti
        self.__updateActiveSeeksLabel()
        self.widgets["seektreeview"].scroll_to_cell(self.store.get_path(ti))

    def onChallengeRemove (self, challenge):
        log.debug("onChallengeRemove: %s" % repr(challenge))
        try:
            ti = self.challenges[hash(challenge)]
        except KeyError:
            pass
        else:
            if self.store.iter_is_valid(ti):
                self.store.remove(ti)
            del self.challenges[hash(challenge)]

        try:
            message = self.messages[hash(challenge)]
        except KeyError:
            pass
        else:
            message.dismiss()
            del self.messages[hash(challenge)]
        self.__updateActiveSeeksLabel()

    def our_seeks_removed (self):
        self.widgets["clearSeeksButton"].set_sensitive(False)
    
    def onAcceptClicked (self, button):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        sought = model.get_value(iter, 0)
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

    def onDeclineClicked (self, button):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        sought = model.get_value(iter, 0)
        self.connection.om.declineIndex(sought.index)

        try:
            message = self.messages[hash(sought)]
        except KeyError:
            pass
        else:
            message.dismiss()
            del self.messages[hash(sought)]
        
    def onClearSeeksClicked (self, button):
        self.connection.client.run_command("unseek")
        self.widgets["clearSeeksButton"].set_sensitive(False)
    
    def row_activated (self, treeview, path, view_column):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        sought = model.get_value(iter, 0)
        if self.lastSeekSelected is None or \
            sought.index != self.lastSeekSelected.index: return
        if path != model.get_path(iter): return
        self.onAcceptClicked(None)

    def onSelectionChanged (self, selection):
        model, iter = selection.get_selected()
        sought = None
        a_seek_is_selected = False
        selection_is_challenge = False
        if iter != None:
            a_seek_is_selected = True
            sought = model.get_value(iter, 0)
            if isinstance(sought, FICSChallenge):
                selection_is_challenge = True
        
        self.lastSeekSelected = sought
        self.widgets["acceptButton"].set_sensitive(a_seek_is_selected)
        self.widgets["declineButton"].set_sensitive(selection_is_challenge)
    
    def _clear_messages (self):
        for message in self.messages.values():
            message.dismiss()
        self.messages.clear()
    
    def onPlayingGame (self):
        self._clear_messages()
        self.widgets["seekListContent"].set_sensitive(False)
        self.widgets["clearSeeksButton"].set_sensitive(False)
        self.__updateActiveSeeksLabel()

    def onCurGameEnded (self):
        self.widgets["seekListContent"].set_sensitive(True)

########################################################################
# Initialize Seek Graph                                                #
########################################################################

YMARKS = (800, 1600, 2400)
YLOCATION = lambda y: min(y/3000.,3000)
XMARKS = (5, 15)
XLOCATION = lambda x: e**(-6.579/(x+1))

# This is used to convert increment time to minutes. With a GAME_LENGTH on
# 40, a game on two minutes and twelve secconds will be placed at the same
# X location as a game on 2+12*40/60 = 10 minutes
GAME_LENGTH = 40

class SeekGraphSection (ParrentListSection):

    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)

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

        self.connection.seeks.connect("FICSSeekCreated", lambda seeks, seek:
            self.listPublisher.put((self.onAddSought, seek)))
        self.connection.seeks.connect("FICSSeekRemoved", lambda seeks, seek:
            self.listPublisher.put((self.onRemoveSought, seek)))
        self.connection.challenges.connect("FICSChallengeIssued",
            lambda challenges, challenge: \
            self.listPublisher.put((self.onAddSought, challenge)))
        self.connection.challenges.connect("FICSChallengeRemoved",
            lambda challenges, challenge: \
            self.listPublisher.put((self.onRemoveSought, challenge)))
        self.connection.bm.connect("playGameCreated", lambda bm, game:
                self.listPublisher.put((self.onPlayingGame,)) )
        self.connection.bm.connect("curGameEnded", lambda bm, game:
                self.listPublisher.put((self.onCurGameEnded,)) )

    def onSpotClicked (self, graph, name):
        self.connection.bm.play(name)
    
    def onAddSought (self, sought):
        x = XLOCATION(float(sought.minutes) + float(sought.inc) * GAME_LENGTH/60.)
        y = YLOCATION(float(sought.player.getRating(sought.game_type.rating_type).elo))
        type_ = 0 if sought.rated else 1
        if isinstance(sought, FICSChallenge):
            tooltip_text = get_challenge_tooltip_text(sought)
        else:
            tooltip_text = get_seek_tooltip_text(sought)
        self.graph.addSpot(sought.index, tooltip_text, x, y, type_)

    def onRemoveSought (self, sought):
        self.graph.removeSpot(sought.index)

    def onPlayingGame (self):
        self.widgets["seekGraphContent"].set_sensitive(False)

    def onCurGameEnded (self):
        self.widgets["seekGraphContent"].set_sensitive(True)

########################################################################
# Initialize Players List                                              #
########################################################################

class PlayerTabSection (ParrentListSection):
    
    widgets = []
    
    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)

        PlayerTabSection.widgets = widgets
        self.connection = connection
        
        self.players = {}
        
        self.tv = widgets["playertreeview"]
        self.store = gtk.ListStore(FICSPlayer, gtk.gdk.Pixbuf, str, int, int,
                                   int, int, int, int, int, int, int, str, str)
        self.tv.set_model(gtk.TreeModelSort(self.store))
        self.addColumns(self.tv, "FICSPlayer", "", _("Name"), _("Blitz"),
            _("Standard"), _("Lightning"), _("Atomic"), _("Bughouse"), _("Crazyhouse"),
            _("Losers"), _("Suicide"), _("Wild"), _("Status"), "tooltip", hide=[0,6,7,8,9,10,11,13],
            pix=[1])
        self.tv.set_tooltip_column(13,)
        self.tv.get_column(0).set_sort_column_id(0)
        self.tv.get_model().set_sort_func(0, self.pixCompareFunction, 1)
        try:
            self.tv.set_search_position_func(self.lowLeftSearchPosFunc)
        except AttributeError:
            # Unknow signal name is raised by gtk < 2.10
            pass

        connection.players.connect("FICSPlayerEntered", self.onPlayerAdded)
        connection.players.connect("FICSPlayerExited", self.onPlayerRemoved)

        widgets["private_chat_button"].connect("clicked", self.onPrivateChatClicked)
        widgets["private_chat_button"].set_sensitive(False)
        widgets["observe_button"].connect("clicked", self.onObserveClicked)
        widgets["observe_button"].set_sensitive(False)
        
        self.tv.get_selection().connect_after("changed", self.onSelectionChanged)
        self.onSelectionChanged(None)
    
    @glock.glocked
    def onPlayerAdded (self, players, player):
        if player in self.players: return
        
        ti = self.store.append([player, player.getIcon(),
            player.name + player.display_titles(), player.blitz, player.standard,
            player.lightning, player.atomic, player.bughouse, player.crazyhouse,
            player.losers, player.suicide, player.wild, player.display_status,
            get_player_tooltip_text(player)])
        self.players[player] = { "ti": ti }
        self.players[player]["status"] = player.connect(
            "notify::status", self.status_changed)
        self.players[player]["game"] = player.connect(
            "notify::game", self.status_changed)
        self.players[player]["titles"] = player.connect(
            "notify::titles", self.titles_changed)
        if player.game:
            self.players[player]["private"] = player.game.connect(
                "notify::private", self.private_changed, player)
        for rt in (TYPE_BLITZ, TYPE_STANDARD, TYPE_LIGHTNING, TYPE_ATOMIC, TYPE_BUGHOUSE,
                   TYPE_CRAZYHOUSE, TYPE_LOSERS, TYPE_SUICIDE, TYPE_WILD):
            self.players[player][rt] = player.ratings[rt].connect(
                "notify::elo", self.elo_changed, player)
        
        count = len(self.players)
        self.widgets["playersOnlineLabel"].set_text(_("Players: %d") % count)
        
    @glock.glocked
    def onPlayerRemoved (self, players, player):
        if player not in self.players: return

        if self.store.iter_is_valid(self.players[player]["ti"]):
            ti = self.players[player]["ti"]
            self.store.remove(ti)
        for key in ("status", "game", "titles"):
            if player.handler_is_connected(self.players[player][key]):
                player.disconnect(self.players[player][key])
        if player.game and "private" in self.players[player] and \
            player.game.handler_is_connected(
                self.players[player]["private"]):
            player.game.disconnect(self.players[player]["private"])
        for rt in (TYPE_BLITZ, TYPE_STANDARD, TYPE_LIGHTNING, TYPE_ATOMIC, TYPE_BUGHOUSE,
                   TYPE_CRAZYHOUSE, TYPE_LOSERS, TYPE_SUICIDE, TYPE_WILD):
            if player.ratings[rt].handler_is_connected(
                    self.players[player][rt]):
                player.ratings[rt].disconnect(self.players[player][rt])
        del self.players[player]
        
        count = len(self.players)
        self.widgets["playersOnlineLabel"].set_text(_("Players: %d") % count)
    
    @glock.glocked
    def status_changed (self, player, property):
        if player not in self.players: return

        if self.store.iter_is_valid(self.players[player]["ti"]):
            self.store.set(self.players[player]["ti"], 12, player.display_status)
            self.store.set(self.players[player]["ti"], 13,
                           get_player_tooltip_text(player))
        
        if player.status == IC_STATUS_PLAYING and player.game and \
                "private" not in self.players[player]:
            self.players[player]["private"] = player.game.connect(
                "notify::private", self.private_changed, player)
        elif player.status != IC_STATUS_PLAYING and \
                "private" in self.players[player]:
            game = player.game
            if game and game.handler_is_connected(self.players[player]["private"]):
                game.disconnect(self.players[player]["private"]) 
            del self.players[player]["private"]
        
        if player == self.getSelectedPlayer():
            self.onSelectionChanged(None)
            
        return False
    
    @glock.glocked
    def titles_changed (self, player, property):
        if player not in self.players: return
        if not self.store.iter_is_valid(self.players[player]["ti"]): return
        self.store.set(self.players[player]["ti"], 1, player.getIcon())
        self.store.set(self.players[player]["ti"], 2,
                       player.name + player.display_titles())
        self.store.set(self.players[player]["ti"], 13,
                       get_player_tooltip_text(player))
        return False
        
    def private_changed (self, game, property, player):
        self.status_changed(player, property)
        self.onSelectionChanged(self.tv.get_selection())
        return False
    
    @glock.glocked
    def elo_changed (self, rating, prop, player):
#        log.debug("elo_changed: %s %s" % (rating.elo, player))
        if player not in self.players: return
        if not self.store.iter_is_valid(self.players[player]["ti"]): return
        ti = self.players[player]["ti"]
#        log.debug("elo_changed: %s" % (self.store.get(ti, 13)))
        self.store.set(ti, 1, player.getIcon())
        self.store.set(self.players[player]["ti"], 13,
                       get_player_tooltip_text(player))
        
        if rating.type == TYPE_BLITZ:
            self.store.set(ti, 3, player.blitz)
        elif rating.type == TYPE_STANDARD:
            self.store.set(ti, 4, player.standard)
        elif rating.type == TYPE_LIGHTNING:
            self.store.set(ti, 5, player.lightning)
        elif rating.type == TYPE_ATOMIC:
            self.store.set(ti, 6, player.atomic)
        elif rating.type == TYPE_BUGHOUSE:
            self.store.set(ti, 7, player.bughouse)
        elif rating.type == TYPE_CRAZYHOUSE:
            self.store.set(ti, 8, player.crazyhouse)
        elif rating.type == TYPE_LOSERS:
            self.store.set(ti, 9, player.losers)
        elif rating.type == TYPE_SUICIDE:
            self.store.set(ti, 10, player.suicide)
        elif rating.type == TYPE_WILD:
            self.store.set(ti, 11, player.wild)
        
        return False
    
    @classmethod
    def getSelectedPlayer (cls):
        model, iter = cls.widgets["playertreeview"].get_selection().get_selected()
        if iter == None: return None
        return model.get_value(iter, 0)
    
    def onPrivateChatClicked (self, button):
        player = self.getSelectedPlayer()
        if player is None: return
        for section in sections:
            if isinstance(section, ChatWindow):
                section.openChatWithPlayer(player.name)
                #TODO: isadmin og type
    
    def onObserveClicked (self, button):        
        player = self.getSelectedPlayer()
        if player is not None and player.game is not None:
            self.connection.bm.observe(player.game)
            
    @glock.glocked
    def onSelectionChanged (self, selection):
        '''When the player selects a player from the player list, update the clickability of our buttons.'''
        player = self.getSelectedPlayer()
        user_name = self.connection.getUsername()
        self.widgets["private_chat_button"].set_sensitive(player is not None)
        self.widgets["observe_button"].set_sensitive(
            player is not None and player.isObservable()\
            and user_name not in (player.game.wplayer.name, player.game.bplayer.name))
        self.widgets["challengeButton"].set_sensitive(
            player is not None and player.isAvailableForGame() and player.name!=user_name)
        
########################################################################
# Initialize Games List                                                #
########################################################################

class GameTabSection (ParrentListSection):

    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)

        self.widgets = widgets
        self.connection = connection

        self.games = {}

        self.recpix = load_icon(16, "media-record")
        self.clearpix = pixbuf_new_from_file(addDataPrefix("glade/board.png"))

        self.tv = self.widgets["gametreeview"]
        self.store = gtk.ListStore(FICSGame, gtk.gdk.Pixbuf, str, int, str, int, str, int)
        self.tv.set_model(gtk.TreeModelSort(self.store))
        self.model = self.tv.get_model()
        self.tv.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.addColumns (
                self.tv, "FICSGame", "", _("White Player"), _("Rating"),
                _("Black Player"), _("Rating"),
                _("Game Type"), "Time", hide=[0,7], pix=[1] )
        self.tv.get_column(0).set_sort_column_id(0)
        self.model.set_sort_func(0, self.pixCompareFunction, 1)
        self.tv.set_has_tooltip(True)
        self.tv.connect("query-tooltip", self.on_query_tooltip)
        
        self.selection = self.tv.get_selection()
        self.selection.connect("changed", self.onSelectionChanged)
        self.onSelectionChanged(self.selection)
        
        def typeCompareFunction (treemodel, iter0, iter1):
            return cmp (treemodel.get_value(iter0, 7),
                        treemodel.get_value(iter1, 7))
        self.model.set_sort_func(6, typeCompareFunction)

        try:
            self.tv.set_search_position_func(self.lowLeftSearchPosFunc)
        except AttributeError:
            # Unknow signal name is raised by gtk < 2.10
            pass
        def searchCallback (model, column, key, iter):
            if model.get_value(iter, 2).lower().startswith(key) or \
                model.get_value(iter, 4).lower().startswith(key):
                return False
            return True
        self.tv.set_search_equal_func (searchCallback)

        self.connection.games.connect("FICSGameCreated", lambda games, game:
                self.listPublisher.put((self.onGameAdd, game)) )
        self.connection.games.connect("FICSGameEnded", lambda games, game:
                self.listPublisher.put((self.onGameRemove, game)) )
        self.widgets["observeButton"].connect ("clicked", self.onObserveClicked)
        self.tv.connect("row-activated", self.onObserveClicked)
        self.connection.bm.connect("obsGameCreated", lambda bm, game:
                self.listPublisher.put((self.onGameObserved, game)) )
        self.connection.bm.connect("obsGameUnobserved", lambda bm, game:
                self.listPublisher.put((self.onGameUnobserved, game)) )

    def on_query_tooltip (self, widget, x, y, keyboard_tip, tooltip):
        if not widget.get_tooltip_context(x, y, keyboard_tip):
            return False
        model, path, iter = widget.get_tooltip_context(x, y, keyboard_tip)
        bin_x, bin_y = widget.convert_widget_to_bin_window_coords(x, y)
        result = widget.get_path_at_pos(bin_x, bin_y)
        
        if result is not None:
            path, column, cell_x, cell_y = result
            for player, column_number in ((self.model[path][0].wplayer, 1),
                                          (self.model[path][0].bplayer, 3)):
                if column is self.tv.get_column(column_number):
                    tooltip.set_text(get_player_tooltip_text(player, show_status=False))
                    widget.set_tooltip_cell(tooltip, path, None, None)
                    return True
        return False
        
    def onSelectionChanged (self, selection):
        model, paths = selection.get_selected_rows()
        a_selected_game_is_observable = False
        for path in paths:
            rowiter = model.get_iter(path)
            game = model.get_value(rowiter, 0)
            if not game.private and game.supported:
                a_selected_game_is_observable = True
                break
        self.widgets["observeButton"].set_sensitive(a_selected_game_is_observable)
    
    def _update_gamesrunning_label (self):
        count = len(self.games)
        self.widgets["gamesRunningLabel"].set_text(_("Games running: %d") % count)

    def onGameAdd (self, game):
#        log.debug("GameTabSection.onGameAdd: %s" % repr(game))
        if game.minutes != None:
            length = game.minutes*60 + game.inc*40
        elif game.game_type.rating_type == TYPE_LIGHTNING:
            length = 100
        elif game.game_type.rating_type == TYPE_BLITZ:
            length = 9*60
        elif game.game_type.rating_type == TYPE_STANDARD:
            length = 15*60
        else:
            length = 0
        
        ti = self.store.append ([game, self.clearpix,
            game.wplayer.name + game.wplayer.display_titles(),
            game.wplayer.getRatingForCurrentGame() or 0,
            game.bplayer.name + game.bplayer.display_titles(),
            game.bplayer.getRatingForCurrentGame() or 0,
            game.display_text, length])
        self.games[game] = { "ti": ti }
        self.games[game]["private_cid"] = game.connect("notify::private",
                                                       self.private_changed)
        self._update_gamesrunning_label()
    
    @glock.glocked
    def private_changed (self, game, property):
        if game in self.games and \
                self.store.iter_is_valid(self.games[game]["ti"]):
            self.store.set(self.games[game]["ti"], 6, game.display_text)
        self.onSelectionChanged(self.tv.get_selection())
        return False
        
    def onGameRemove (self, game):
        if game not in self.games: return
        if self.store.iter_is_valid(self.games[game]["ti"]):
            self.store.remove(self.games[game]["ti"])
        if game.handler_is_connected(self.games[game]["private_cid"]):
            game.disconnect(self.games[game]["private_cid"])
        del self.games[game]
        self._update_gamesrunning_label()

    def onObserveClicked (self, widget, *args):
        model, paths = self.tv.get_selection().get_selected_rows()
        for path in paths:
            rowiter = model.get_iter(path)
            game = model.get_value(rowiter, 0)
            self.connection.bm.observe(game)

    def onGameObserved (self, game):
        if game in self.games:
            treeiter = self.games[game]["ti"]
            self.store.set_value(treeiter, 1, self.recpix)

    def onGameUnobserved (self, game):
        if game in self.games:
            treeiter = self.games[game]["ti"]
            self.store.set_value(treeiter, 1, self.clearpix)

########################################################################
# Initialize Adjourned List                                            #
########################################################################

class AdjournedTabSection (ParrentListSection):

    def __init__ (self, widgets, connection, infobar):
        ParrentListSection.__init__(self)
        self.connection = connection
        self.widgets = widgets
        self.infobar = infobar
        self.games = {}
        self.messages = {}
        
        self.wpix = pixbuf_new_from_file(addDataPrefix("glade/white.png"))
        self.bpix = pixbuf_new_from_file(addDataPrefix("glade/black.png"))
        
        self.tv = widgets["adjournedtreeview"]
        self.store = gtk.ListStore(FICSAdjournedGame, gtk.gdk.Pixbuf, str, str,
                                   str, str, str)
        self.tv.set_model(gtk.TreeModelSort(self.store))
        self.addColumns (self.tv, "FICSAdjournedGame", _("Your Color"),
            _("Opponent"), _("Is Online"), _("Time Control"), _("Game Type"),
            _("Date/Time"), hide=[0], pix=[1])
        self.selection = self.tv.get_selection()
        self.selection.connect("changed", self.onSelectionChanged)
        self.onSelectionChanged(self.selection)

        self.connection.adm.connect("adjournedGameAdded", lambda adm, game:
                self.listPublisher.put((self.onAdjournedGameAdded, game)) )
        self.connection.games.connect("FICSAdjournedGameRemoved", lambda games, game:
                self.listPublisher.put((self.onAdjournedGameRemoved, game)) )

        widgets["resignButton"].connect("clicked", self.onResignButtonClicked)
        widgets["abortButton"].connect("clicked", self.onAbortButtonClicked)
        widgets["drawButton"].connect("clicked", self.onDrawButtonClicked)
        widgets["resumeButton"].connect("clicked", self.onResumeButtonClicked)
        widgets["previewButton"].connect("clicked", self.onPreviewButtonClicked)
        self.tv.connect("row-activated", lambda *args: self.onPreviewButtonClicked(None))
        self.connection.adm.connect("adjournedGamePreview", lambda adm, game:
            self.listPublisher.put((self.onGamePreview, game)))
        self.connection.bm.connect("playGameCreated", self.onPlayGameCreated)
        
    def onSelectionChanged (self, selection):
        model, treeiter = selection.get_selected()
        a_row_is_selected = False
        if treeiter != None:
            a_row_is_selected = True
            game = model.get_value(treeiter, 0)
            update_button_by_player_status(self.widgets["resumeButton"], game.opponent)
        else:
            self.widgets["resumeButton"].set_sensitive(False)
            self.widgets["resumeButton"].set_tooltip_text("")
        for button in ("resignButton", "abortButton", "drawButton", "previewButton"):
            self.widgets[button].set_sensitive(a_row_is_selected)
        
    @glock.glocked
    def onPlayGameCreated (self, bm, board):
        for message in self.messages.values():
            message.dismiss()
        self.messages = {}
        return False
        
    def _infobar_adjourned_message (self, game, player):
        if player not in self.messages:
            text = _(" with whom you have an adjourned <b>%(timecontrol)s</b> <b>%(gametype)s</b> " + \
                "game is online.")  % \
                {"timecontrol": game.display_timecontrol, "gametype": game.game_type.display_text}
            content = self.get_infobarmessage_content(player, text,
                                                      gametype=game.game_type)
            def callback (infobar, response, message):
                if response == gtk.RESPONSE_ACCEPT:
                    self.connection.client.run_command("match %s" % player.name)
                elif response == gtk.RESPONSE_HELP:
                    self.connection.adm.queryMoves(game)
                else:
                    try:
                        self.messages[player].dismiss()
                        del self.messages[player]
                    except KeyError: pass
                return False
            message = InfoBarMessage(gtk.MESSAGE_QUESTION, content, callback)
            message.add_button(InfoBarMessageButton(_("Request Continuation"),
                                                    gtk.RESPONSE_ACCEPT))
            message.add_button(InfoBarMessageButton(_("Examine Adjourned Game"),
                                                    gtk.RESPONSE_HELP))
            message.add_button(InfoBarMessageButton(gtk.STOCK_CLOSE,
                                                    gtk.RESPONSE_CANCEL))
            update_button_by_player_status(message.buttons[0], player)
            self.messages[player] = message
            self.infobar.push_message(message)
            
    @glock.glocked
    def online_changed (self, player, property, game):
        log.debug("AdjournedTabSection.online_changed: %s %s" % \
            (repr(player), repr(game)))
        if game in self.games and \
                self.store.iter_is_valid(self.games[game]["ti"]):
            self.store.set(self.games[game]["ti"], 3, player.display_online)
        
        if player.online and player.adjournment:
            self._infobar_adjourned_message(game, player)
        elif not player.online and player in self.messages:
            self.messages[player].dismiss()
            # calling message.dismiss() might cause it to be removed from
            # self.messages in another callback, so we re-check
            if player in self.messages:
                del self.messages[player]
        
        return False
        
    @glock.glocked
    def status_changed (self, player, prop, game):
        log.debug("AdjournedTabSection.status_changed: %s %s" % \
            (repr(player), repr(game)))
        try:
            message = self.messages[player]
        except KeyError:
            pass
        else:
            update_button_by_player_status(message.buttons[0], player)
        self.onSelectionChanged(self.selection)
        return False
        
    def onAdjournedGameAdded (self, game):
        if game not in self.games:
            pix = (self.wpix, self.bpix)[game.our_color]
            ti = self.store.append([game, pix, game.opponent.name,
                game.opponent.display_online, game.display_timecontrol,
                game.game_type.display_text, game.display_time])
            self.games[game] = {}
            self.games[game]["ti"] = ti
            self.games[game]["online_cid"] = game.opponent.connect(
                "notify::online", self.online_changed, game)
            self.games[game]["status_cid"] = game.opponent.connect(
                "notify::status", self.status_changed, game)
        
        if game.opponent.online:
            self._infobar_adjourned_message(game, game.opponent)
        
        return False
    
    def onAdjournedGameRemoved (self, game):
        if game in self.games:
            if self.store.iter_is_valid(self.games[game]["ti"]):
                self.store.remove(self.games[game]["ti"])
            if game.opponent.handler_is_connected(self.games[game]["online_cid"]):
                game.opponent.disconnect(self.games[game]["online_cid"])
            if game.opponent.handler_is_connected(self.games[game]["status_cid"]):
                game.opponent.disconnect(self.games[game]["status_cid"])
            if game.opponent in self.messages:
                self.messages[game.opponent].dismiss()
                if game.opponent in self.messages:
                    del self.messages[game.opponent]
            del self.games[game]
        
        return False
    
    def onResignButtonClicked (self, button):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        game = model.get_value(iter, 0)
        self.connection.adm.resign(game)
    
    def onDrawButtonClicked (self, button):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        game = model.get_value(iter, 0)
        self.connection.adm.draw(game)
    
    def onAbortButtonClicked (self, button):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        game = model.get_value(iter, 0)
        self.connection.adm.abort(game)
    
    def onResumeButtonClicked (self, button):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        game = model.get_value(iter, 0)
        self.connection.adm.resume(game)
    
    def onPreviewButtonClicked (self, button):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        game = model.get_value(iter, 0)
        self.connection.adm.queryMoves(game)

    def onGamePreview (self, ficsgame):
        log.debug("ICLounge.onGamePreview: %s" % ficsgame)
        if ficsgame.board.wms == 0 and ficsgame.board.bms == 0:
            timemodel = None
        else:
            timemodel = TimeModel(ficsgame.board.wms/1000., ficsgame.inc,
                bsecs=ficsgame.board.bms/1000., minutes=ficsgame.minutes)
        gamemodel = ICGameModel(self.connection, ficsgame, timemodel)
        
        # The players need to start listening for moves IN this method if they
        # want to be noticed of all moves the FICS server sends us from now on.
        # Hence the lazy loading is skipped.
        wplayer, bplayer = ficsgame.wplayer, ficsgame.bplayer
        player0 = ICPlayer(gamemodel, wplayer.name, -1, WHITE,
            wplayer.long_name(game_type=ficsgame.game_type),
            icrating=wplayer.getRating(ficsgame.game_type.rating_type).elo)
        player1 = ICPlayer(gamemodel, bplayer.name, -1, BLACK,
            bplayer.long_name(game_type=ficsgame.game_type),
            icrating=bplayer.getRating(ficsgame.game_type.rating_type).elo)
        
        player0tup = (REMOTE, lambda:player0, (), wplayer.long_name())
        player1tup = (REMOTE, lambda:player1, (), bplayer.long_name())
        
        ionest.generalStart(gamemodel, player0tup, player1tup,
                            (StringIO(ficsgame.board.pgn), pgn, 0, -1))
        gamemodel.connect("game_started", lambda gamemodel:
                          gamemodel.end(ADJOURNED, ficsgame.reason))
        
############################################################################
# Initialize "Create Seek" and "Challenge" panels, and "Edit Seek:" dialog #
############################################################################

RATING_SLIDER_STEP = 25
    
class SeekChallengeSection (ParrentListSection):
    
    seekEditorWidgets = (
        "untimedCheck", "minutesSpin", "gainSpin",
        "strengthCheck", "chainAlignment", "ratingCenterSlider", "toleranceSlider", "toleranceHBox",
        "nocolorRadio", "whitecolorRadio", "blackcolorRadio",
        # variantCombo has to come before other variant widgets so that
        # when the widget is loaded, variantRadio isn't selected by the callback,
        # overwriting the user's saved value for the variant radio buttons
        "variantCombo", "noVariantRadio", "variantRadio",
        "ratedGameCheck", "manualAcceptCheck" )
    
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
    
    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)
        
        self.widgets = widgets
        self.connection = connection
        
        self.finger = None
        conf.set("numberOfFingers", 0)
        glock.glock_connect(self.connection.fm, "fingeringFinished",
            lambda fm, finger: self.onFinger(fm, finger))
        self.connection.fm.finger(self.connection.getUsername())
        
        self.widgets["untimedCheck"].connect("toggled", self.onUntimedCheckToggled)
        self.widgets["minutesSpin"].connect("value-changed", self.onTimeSpinChanged)
        self.widgets["gainSpin"].connect("value-changed", self.onTimeSpinChanged)
        self.onTimeSpinChanged(self.widgets["minutesSpin"])
        
        self.widgets["nocolorRadio"].connect("toggled", self.onColorRadioChanged)
        self.widgets["whitecolorRadio"].connect("toggled", self.onColorRadioChanged)
        self.widgets["blackcolorRadio"].connect("toggled", self.onColorRadioChanged)
        self.onColorRadioChanged(self.widgets["nocolorRadio"])
        
        self.widgets["noVariantRadio"].connect("toggled", self.onVariantRadioChanged)
        self.widgets["variantRadio"].connect("toggled", self.onVariantRadioChanged)
        variantComboGetter, variantComboSetter = self.__initVariantCombo(self.widgets["variantCombo"])
        self.seekEditorWidgetGettersSetters["variantCombo"] = (variantComboGetter, variantComboSetter)
        self.widgets["variantCombo"].connect("changed", self.onVariantComboChanged)

        self.widgets["editSeekDialog"].connect("delete_event", lambda *a: True)
        glock.glock_connect(self.connection, "disconnected",
            lambda c: self.widgets and self.widgets["editSeekDialog"].response(gtk.RESPONSE_CANCEL))
        glock.glock_connect(self.connection, "disconnected",
            lambda c: self.widgets and self.widgets["challengeDialog"].response(gtk.RESPONSE_CANCEL))

        self.widgets["strengthCheck"].connect("toggled", self.onStrengthCheckToggled)
        self.onStrengthCheckToggled(self.widgets["strengthCheck"])
        self.widgets["ratingCenterSlider"].connect("value-changed", self.onRatingCenterSliderChanged)
        self.onRatingCenterSliderChanged(self.widgets["ratingCenterSlider"])
        self.widgets["toleranceSlider"].connect("value-changed", self.onToleranceSliderChanged)
        self.onToleranceSliderChanged(self.widgets["toleranceSlider"])
        self.widgets["toleranceButton"].connect("clicked", self.onToleranceButtonClicked)
        def toleranceHBoxGetter (widget):
            return self.widgets["toleranceHBox"].get_property("visible")
        def toleranceHBoxSetter (widget, visible):
            assert type(visible) is bool
            if visible:
                self.widgets["toleranceHBox"].show()
            else:
                self.widgets["toleranceHBox"].hide()
        self.seekEditorWidgetGettersSetters["toleranceHBox"] = (toleranceHBoxGetter, toleranceHBoxSetter)
        
        self.chainbox = ChainVBox()
        self.widgets["chainAlignment"].add(self.chainbox)
        def chainboxGetter (widget):
            return self.chainbox.active
        def chainboxSetter (widget, is_active):
            self.chainbox.active = is_active
        self.seekEditorWidgetGettersSetters["chainAlignment"] = (chainboxGetter, chainboxSetter)
        
        self.challengee = None
        self.in_challenge_mode = False
        self.seeknumber = 1
        self.widgets["seekButton"].connect("clicked", self.onSeekButtonClicked)
        self.widgets["challengeButton"].connect("clicked", self.onChallengeButtonClicked)
        self.widgets["challengeDialog"].connect("delete-event", self.onChallengeDialogResponse)
        self.widgets["challengeDialog"].connect("response", self.onChallengeDialogResponse)
        self.widgets["editSeekDialog"].connect("response", self.onEditSeekDialogResponse)
        
        for widget in ("seek1Radio", "seek2Radio", "seek3Radio",
                       "challenge1Radio", "challenge2Radio", "challenge3Radio"):
            uistuff.keep(self.widgets[widget], widget)
        
        self.lastdifference = 0
        self.loading_seek_editor = False
        self.savedSeekRadioTexts = [ GAME_TYPES["blitz"].display_text ] * 3
        
        for i in range(1,4):
            self.__loadSeekEditor(i)
            self.__writeSavedSeeks(i)
            self.widgets["seek%sRadioConfigButton" % i].connect(
                "clicked", self.onSeekRadioConfigButtonClicked, i)
            self.widgets["challenge%sRadioConfigButton" % i].connect(
                "clicked", self.onChallengeRadioConfigButtonClicked, i)
        
        if not self.connection.isRegistred():
            self.chainbox.active = False
            self.widgets["chainAlignment"].set_sensitive(False)
            self.widgets["chainAlignment"].set_tooltip_text(_("The chain button is disabled because you are logged in as a guest. Guests can't establish ratings, and the chain button's state has no effect when there is no rating to which to tie \"Opponent Strength\" to"))
    
    def onSeekButtonClicked (self, button):
        if self.widgets["seek3Radio"].get_active():
            self.__loadSeekEditor(3)
        elif self.widgets["seek2Radio"].get_active():
            self.__loadSeekEditor(2)
        else:
            self.__loadSeekEditor(1)
        
        min, incr, gametype, ratingrange, color, rated, manual = self.__getSeekEditorDialogValues()
        self.connection.glm.seek(min, incr, gametype, rated, ratingrange, color, manual)

    def onChallengeButtonClicked (self, button):
        player = PlayerTabSection.getSelectedPlayer()
        if player is None: return
        self.challengee = player
        self.in_challenge_mode = True
        
        for i in range(1,4):
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
        self.widgets["challengeeImage"].set_from_pixbuf(player.getIcon(size=32))
        title = _("Challenge: ") + player.name
        self.widgets["challengeDialog"].set_title(title)
        self.widgets["challengeDialog"].present()
    
    def onChallengeDialogResponse (self, dialog, response):
        self.widgets["challengeDialog"].hide()
        if response is not 5:
            return True
        
        if self.widgets["challenge3Radio"].get_active():
            self.__loadSeekEditor(3)
        elif self.widgets["challenge2Radio"].get_active():
            self.__loadSeekEditor(2)
        else:
            self.__loadSeekEditor(1)
        min, incr, gametype, ratingrange, color, rated, manual = self.__getSeekEditorDialogValues()
        self.connection.om.challenge(self.challengee.name, gametype, min, incr, rated, color)
    
    def onSeekRadioConfigButtonClicked (self, configimage, seeknumber): 
        self.__showSeekEditor(seeknumber)
    
    def onChallengeRadioConfigButtonClicked (self, configimage, seeknumber):
        self.__showSeekEditor(seeknumber, challengemode=True)
        
    def onEditSeekDialogResponse (self, dialog, response):
        self.widgets["editSeekDialog"].hide()
        if response != gtk.RESPONSE_OK:
            return
        self.__saveSeekEditor(self.seeknumber)
        self.__writeSavedSeeks(self.seeknumber)
    
    def __updateSeekEditor (self, seeknumber, challengemode=False):
        self.in_challenge_mode = challengemode
        self.seeknumber = seeknumber
        if not challengemode:
            self.widgets["strengthFrame"].set_sensitive(True)
            self.widgets["strengthFrame"].set_tooltip_text("")
            self.widgets["manualAcceptCheck"].set_sensitive(True)
            self.widgets["manualAcceptCheck"].set_tooltip_text("")
        else:
            self.widgets["strengthFrame"].set_sensitive(False)
            self.widgets["strengthFrame"].set_tooltip_text(
                _("This option is not applicable because you're challenging a player"))
            self.widgets["manualAcceptCheck"].set_sensitive(False)
            self.widgets["manualAcceptCheck"].set_tooltip_text(
                _("This option is not applicable because you're challenging a player"))
        
        self.widgets["chainAlignment"].show_all()        
        self.__loadSeekEditor(seeknumber)
        self.widgets["seek%dRadio" % seeknumber].set_active(True)
        self.widgets["challenge%dRadio" % seeknumber].set_active(True)
        
        self.__updateYourRatingHBox()
        self.__updateRatingCenterInfoBox()
        self.__updateToleranceButton()
        self.__updateRatedGameCheck()
        self.onUntimedCheckToggled(self.widgets["untimedCheck"])
        
        title = _("Edit Seek: ") + self.widgets["seek%dRadio" % seeknumber].get_label()[:-1]
        self.widgets["editSeekDialog"].set_title(title)
        
    def __showSeekEditor (self, seeknumber, challengemode=False):
        self.__updateSeekEditor(seeknumber, challengemode)
        self.widgets["editSeekDialog"].present()
    
    #-------------------------------------------------------- Seek Editor
    
    def __writeSavedSeeks (self, seeknumber):
        """ Writes saved seek strings for both the Seek Panel and the Challenge Panel """
        min, gain, gametype, ratingrange, color, rated, manual = \
            self.__getSeekEditorDialogValues()
        self.savedSeekRadioTexts[seeknumber-1] = \
            time_control_to_gametype(min, gain).display_text
        self.__writeSeekRadioLabels()
        seek = {}
        
        if gametype == GAME_TYPES["untimed"]:
            seek["time"] = gametype.display_text
        elif gain > 0:
            seek["time"] = _("%(minutes)d min + %(gain)d sec/move") % \
                {'minutes' : min, 'gain' : gain}
        else:
            seek["time"] = _("%d min") % min
        
        if isinstance(gametype, VariantGameType):
            seek["variant"] = "%s" % gametype.display_text
        
        rrtext = get_rating_range_display_text(ratingrange[0], ratingrange[1])
        if rrtext:
            seek["rating"] = rrtext
        
        if color == WHITE:
            seek["color"] = _("White")
        elif color == BLACK:
            seek["color"] = _("Black")
        
        if rated and gametype != GAME_TYPES["untimed"]:
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
        
    def __loadSeekEditor (self, seeknumber):
        self.loading_seek_editor = True
        for widget in self.seekEditorWidgets:
            if widget in self.seekEditorWidgetGettersSetters:
                uistuff.loadDialogWidget(self.widgets[widget], widget, seeknumber,
                                   get_value_=self.seekEditorWidgetGettersSetters[widget][0],
                                   set_value_=self.seekEditorWidgetGettersSetters[widget][1],
                                   first_value=self.seekEditorWidgetDefaults[widget][seeknumber-1])
            elif widget in self.seekEditorWidgetDefaults:
                uistuff.loadDialogWidget(self.widgets[widget], widget, seeknumber,
                                   first_value=self.seekEditorWidgetDefaults[widget][seeknumber-1])
            else:
                uistuff.loadDialogWidget(self.widgets[widget], widget, seeknumber)
        
        self.lastdifference = conf.get("lastdifference-%d" % seeknumber, -1)
        self.loading_seek_editor = False
        
    def __saveSeekEditor (self, seeknumber):
        for widget in self.seekEditorWidgets:
            if widget in self.seekEditorWidgetGettersSetters:
                uistuff.saveDialogWidget(self.widgets[widget], widget, seeknumber,
                                         get_value_=self.seekEditorWidgetGettersSetters[widget][0])
            else:
                uistuff.saveDialogWidget(self.widgets[widget], widget, seeknumber)
        
        conf.set("lastdifference-%d" % seeknumber, self.lastdifference)

    def __getSeekEditorDialogValues (self):
        if self.widgets["untimedCheck"].get_active():
            min = 0
            incr = 0
        else:
            min = int(self.widgets["minutesSpin"].get_value())
            incr = int(self.widgets["gainSpin"].get_value())
        
        if self.widgets["strengthCheck"].get_active():
            ratingrange = [0, 9999]
        else:
            center = int(self.widgets["ratingCenterSlider"].get_value()) * RATING_SLIDER_STEP
            tolerance = int(self.widgets["toleranceSlider"].get_value()) * RATING_SLIDER_STEP
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
            gametype = time_control_to_gametype(min, incr)
        else:
            variant_combo_getter = self.seekEditorWidgetGettersSetters["variantCombo"][0]
            variant = variant_combo_getter(self.widgets["variantCombo"])
            gametype = VARIANT_GAME_TYPES[variant]

        rated = self.widgets["ratedGameCheck"].get_active() and \
                   not self.widgets["untimedCheck"].get_active()
        manual = self.widgets["manualAcceptCheck"].get_active()
        
        return min, incr, gametype, ratingrange, color, rated, manual
        
    def __writeSeekRadioLabels (self):
        gameTypes = { _("Untimed"): [0, 1], _("Standard"): [0, 1],
                      _("Blitz"): [0, 1], _("Lightning"): [0, 1] }
        
        for i in range(3):
            gameTypes[self.savedSeekRadioTexts[i]][0] += 1
        for i in range(3):
            if gameTypes[self.savedSeekRadioTexts[i]][0] > 1:
                labelText = "%s #%d:" % \
                   (self.savedSeekRadioTexts[i], gameTypes[self.savedSeekRadioTexts[i]][1])
                self.widgets["seek%dRadio" % (i+1)].set_label(labelText)
                self.widgets["challenge%dRadio" % (i+1)].set_label(labelText)
                gameTypes[self.savedSeekRadioTexts[i]][1] += 1
            else:
                self.widgets["seek%dRadio" % (i+1)].set_label(self.savedSeekRadioTexts[i]+":")
                self.widgets["challenge%dRadio" % (i+1)].set_label(self.savedSeekRadioTexts[i]+":")
    
    def __updateRatingRangeBox (self):
        center = int(self.widgets["ratingCenterSlider"].get_value()) * RATING_SLIDER_STEP
        tolerance = int(self.widgets["toleranceSlider"].get_value()) * RATING_SLIDER_STEP
        minRating = center - tolerance
        minRating = minRating > 0 and minRating or 0
        maxRating = center + tolerance
        maxRating = maxRating >= 3000 and 9999 or maxRating 
        
        self.widgets["ratingRangeMinLabel"].set_label("%d" % minRating)
        self.widgets["ratingRangeMaxLabel"].set_label("%d" % maxRating)
        
        for widgetName, rating in (("ratingRangeMinImage", minRating),
                                   ("ratingRangeMaxImage", maxRating)):
            pixbuf = FICSPlayer.getIconByRating(rating)
            self.widgets[widgetName].set_from_pixbuf(pixbuf)
        
        self.widgets["ratingRangeMinImage"].show()
        self.widgets["ratingRangeMinLabel"].show()
        self.widgets["dashLabel"].show()        
        self.widgets["ratingRangeMaxImage"].show()
        self.widgets["ratingRangeMaxLabel"].show()
        if minRating == 0:
            self.widgets["ratingRangeMinImage"].hide()
            self.widgets["ratingRangeMinLabel"].hide()
            self.widgets["dashLabel"].hide()
            self.widgets["ratingRangeMaxLabel"].set_label("%d↓" % maxRating)
        if maxRating == 9999:
            self.widgets["ratingRangeMaxImage"].hide()
            self.widgets["ratingRangeMaxLabel"].hide()
            self.widgets["dashLabel"].hide()            
            self.widgets["ratingRangeMinLabel"].set_label("%d↑" % minRating)
        if minRating == 0 and maxRating == 9999:
            self.widgets["ratingRangeMinLabel"].set_label(_("Any strength"))
            self.widgets["ratingRangeMinLabel"].show()
    
    def __getGameType (self):
        if self.widgets["untimedCheck"].get_active():
            gametype = GAME_TYPES["untimed"]
        elif self.widgets["noVariantRadio"].get_active():
            min = int(self.widgets["minutesSpin"].get_value())
            gain = int(self.widgets["gainSpin"].get_value())
            gametype = time_control_to_gametype(min, gain)
        else:
            variant_combo_getter = self.seekEditorWidgetGettersSetters["variantCombo"][0]
            variant = variant_combo_getter(self.widgets["variantCombo"])
            gametype = VARIANT_GAME_TYPES[variant]
        return gametype
        
    def __updateYourRatingHBox (self):
        gametype = self.__getGameType()
        self.widgets["yourRatingNameLabel"].set_label("(" + gametype.display_text + ")")
        rating = self.__getRating(gametype.rating_type)
        if rating is None:
            self.widgets["yourRatingImage"].clear()
            self.widgets["yourRatingLabel"].set_label(_("Unrated"))
            return
        pixbuf = FICSPlayer.getIconByRating(rating)
        self.widgets["yourRatingImage"].set_from_pixbuf(pixbuf)
        self.widgets["yourRatingLabel"].set_label(str(rating))
        
        center = int(self.widgets["ratingCenterSlider"].get_value()) * RATING_SLIDER_STEP
        rating = self.__clamp(rating)
        difference = rating - center
        if self.loading_seek_editor is False and self.chainbox.active and \
                difference is not self.lastdifference:
            newcenter = rating - self.lastdifference
            self.widgets["ratingCenterSlider"].set_value(newcenter / RATING_SLIDER_STEP)
        else:
            self.lastdifference = difference
    
    def __clamp (self, rating):
        assert type(rating) is int
        mod = rating % RATING_SLIDER_STEP
        if mod > RATING_SLIDER_STEP / 2:
            return rating - mod + RATING_SLIDER_STEP
        else:
            return rating - mod
    
    def __updateRatedGameCheck (self):
        # on FICS, untimed games can't be rated, nor can games against a guest
        if not self.connection.isRegistred():
            self.widgets["ratedGameCheck"].set_active(False)
            sensitive = False
            self.widgets["ratedGameCheck"].set_tooltip_text(
                _("You can't play rated games because you are logged in as a guest"))
        elif self.widgets["untimedCheck"].get_active() :
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
    
    def __initVariantCombo (self, combo):
        model = gtk.TreeStore(str)
        cellRenderer = gtk.CellRendererText()
        combo.clear()
        combo.pack_start(cellRenderer, True)
        combo.add_attribute(cellRenderer, 'text', 0)
        combo.set_model(model)
        
        groupNames = {VARIANTS_SHUFFLE: _("Shuffle"),
                      VARIANTS_OTHER: _("Other (standard rules)"),
                      VARIANTS_OTHER_NONSTANDARD: _("Other (non standard rules)"),
                      }
        ficsvariants = [v for k, v in variants.iteritems() if k in VARIANT_GAME_TYPES and 
                                                    v.board.variant not in UNSUPPORTED]
        groups = groupby(ficsvariants, attrgetter("variant_group"))
        pathToVariant = {}
        variantToPath = {}
        for i, (id, group) in enumerate(groups):
            iter = model.append(None, (groupNames[id],))
            for variant in group:
                subiter = model.append(iter, (variant.name,))
                path = model.get_path(subiter)
                pathToVariant[path] = variant.board.variant
                variantToPath[variant.board.variant] = path
        
        # this stops group names (eg "Shuffle") from being displayed in submenus
        def cellFunc (combo, cell, model, iter, data):
            isChildNode = not model.iter_has_child(iter)
            cell.set_property("sensitive", isChildNode)
        combo.set_cell_data_func(cellRenderer, cellFunc, None)
        
        def comboGetter (combo):
            path = model.get_path(combo.get_active_iter())
            return pathToVariant[path]
            
        def comboSetter (combo, variant):
            if variant not in VARIANT_GAME_TYPES:
                variant = LOSERSCHESS
            combo.set_active_iter(model.get_iter(variantToPath[variant]))
        return comboGetter, comboSetter
    
    def __getRating (self, gametype):
        if self.finger is None: return None
        try:
            ratingobj = self.finger.getRating(type=gametype)
            rating = int(ratingobj.elo)
        except KeyError:  # the user doesn't have a rating for this game type
            rating = None
        return rating
        
    def onFinger (self, fm, finger):
        if not finger.getName() == self.connection.getUsername(): return
        self.finger = finger
        
        numfingers = conf.get("numberOfFingers", 0) + 1
        conf.set("numberOfFingers", numfingers)
        if conf.get("numberOfTimesLoggedInAsRegisteredUser", 0) is 1 and numfingers is 1:
            standard = self.__getRating(TYPE_STANDARD)
            blitz = self.__getRating(TYPE_BLITZ)
            lightning = self.__getRating(TYPE_LIGHTNING)
            
            if standard is not None:
                self.seekEditorWidgetDefaults["ratingCenterSlider"][0] = standard / RATING_SLIDER_STEP
            elif blitz is not None:
                self.seekEditorWidgetDefaults["ratingCenterSlider"][0] = blitz / RATING_SLIDER_STEP
            if blitz is not None:
                self.seekEditorWidgetDefaults["ratingCenterSlider"][1] = blitz / RATING_SLIDER_STEP
            if lightning is not None:
                self.seekEditorWidgetDefaults["ratingCenterSlider"][2] = lightning / RATING_SLIDER_STEP
            elif blitz is not None:
                self.seekEditorWidgetDefaults["ratingCenterSlider"][2] = blitz / RATING_SLIDER_STEP
            
            for i in range(1,4):
                self.__loadSeekEditor(i)
                self.__updateSeekEditor(i)
                self.__saveSeekEditor(i)
                self.__writeSavedSeeks(i)

        self.__updateYourRatingHBox()
    
    def onTimeSpinChanged (self, spin):
        minutes = self.widgets["minutesSpin"].get_value_as_int()
        gain = self.widgets["gainSpin"].get_value_as_int()
        name = time_control_to_gametype(minutes, gain).display_text
        self.widgets["timeControlNameLabel"].set_label("%s" % name)
        self.__updateYourRatingHBox()
    
    def onUntimedCheckToggled (self, check):
        is_untimed_game = check.get_active()
        self.widgets["timeControlConfigVBox"].set_sensitive(not is_untimed_game)
        # on FICS, untimed games can't be rated and can't be a chess variant
        self.widgets["variantFrame"].set_sensitive(not is_untimed_game)
        if is_untimed_game:
            self.widgets["variantFrame"].set_tooltip_text(
                _("You can't select a variant because \"Untimed\" is checked, ") +
                _("and on FICS, untimed games have to be normal chess rules"))
        else:
            self.widgets["variantFrame"].set_tooltip_text("")
        self.__updateRatedGameCheck()  # sets sensitivity of widgets["ratedGameCheck"]
        self.__updateYourRatingHBox()
        
    def onStrengthCheckToggled (self, check):
        strengthsensitive = not check.get_active()
        self.widgets["strengthConfigVBox"].set_sensitive(strengthsensitive)        
        
    def onRatingCenterSliderChanged (self, slider):
        center = int(self.widgets["ratingCenterSlider"].get_value()) * RATING_SLIDER_STEP
        pixbuf = FICSPlayer.getIconByRating(center)
        self.widgets["ratingCenterLabel"].set_label("%d" % (center))
        self.widgets["ratingCenterImage"].set_from_pixbuf(pixbuf)        
        self.__updateRatingRangeBox()

        rating = self.__getRating(self.__getGameType().rating_type)
        if rating is None: return
        rating = self.__clamp(rating)
        self.lastdifference = rating - center
        
    def __updateRatingCenterInfoBox (self):
        if self.widgets["toleranceHBox"].get_property("visible") == True:
            self.widgets["ratingCenterAlignment"].set_property("top-padding", 4)
            self.widgets["ratingCenterInfoHBox"].show()
        else:
            self.widgets["ratingCenterAlignment"].set_property("top-padding", 0)
            self.widgets["ratingCenterInfoHBox"].hide()
    
    def __updateToleranceButton (self):
        if self.widgets["toleranceHBox"].get_property("visible") == True:
            self.widgets["toleranceButton"].set_property("label", _("Hide"))
        else:
            self.widgets["toleranceButton"].set_property("label", _("Change Tolerance"))

    def onToleranceButtonClicked (self, button):
        if self.widgets["toleranceHBox"].get_property("visible") == True:
            self.widgets["toleranceHBox"].hide()
        else:
            self.widgets["toleranceHBox"].show()
        self.__updateToleranceButton()
        self.__updateRatingCenterInfoBox()

    def onToleranceSliderChanged (self, slider):
        tolerance = int(self.widgets["toleranceSlider"].get_value()) * RATING_SLIDER_STEP
        self.widgets["toleranceLabel"].set_label("±%d" % tolerance)
        self.__updateRatingRangeBox()

    def onColorRadioChanged (self, radio):
        if self.widgets["nocolorRadio"].get_active():
            self.widgets["colorImage"].set_from_file(addDataPrefix("glade/piece-unknown.png"))
            self.widgets["colorImage"].set_sensitive(False)
        elif self.widgets["whitecolorRadio"].get_active():
            self.widgets["colorImage"].set_from_file(addDataPrefix("glade/piece-white.png"))
            self.widgets["colorImage"].set_sensitive(True)
        elif self.widgets["blackcolorRadio"].get_active():
            self.widgets["colorImage"].set_from_file(addDataPrefix("glade/piece-black.png"))
            self.widgets["colorImage"].set_sensitive(True)

    def onVariantRadioChanged (self, radio):
        self.__updateYourRatingHBox()
    
    def onVariantComboChanged (self, combo):
        self.widgets["variantRadio"].set_active(True)            
        self.__updateYourRatingHBox()
        min, gain, gametype, ratingrange, color, rated, manual = \
            self.__getSeekEditorDialogValues()
        self.widgets["variantCombo"].set_tooltip_text(
            variants[gametype.variant_type].__desc__)

############################################################################
# Relay server messages which aren't part of a game to the user            #
############################################################################

class PlayerNotificationMessage (InfoBarMessage):
    def __init__ (self, message_type, content, callback, player, text):
        InfoBarMessage.__init__(self, message_type, content, callback)
        self.player = player
        self.text = text

class Messages (Section):
    def __init__ (self, widgets, connection, infobar):
        self.connection = connection
        self.infobar = infobar
        self.messages = []
        self.players = []
        self.connection.bm.connect("tooManySeeks", self.tooManySeeks)
        self.connection.bm.connect("matchDeclined", self.matchDeclined)
        self.connection.bm.connect("playGameCreated", self.onPlayGameCreated)
        self.connection.glm.connect("seek-updated", self.on_seek_updated)
        self.connection.glm.connect("our-seeks-removed", self.our_seeks_removed)
        self.connection.cm.connect("arrivalNotification", self.onArrivalNotification)
        self.connection.cm.connect("departedNotification", self.onDepartedNotification)
        for user in self.connection.notify_users:
            user = self.connection.players.get(FICSPlayer(user))
            self.user_from_notify_list_is_present(user)
        
    @glock.glocked
    def tooManySeeks (self, bm):
        label = gtk.Label(_("You may only have 3 outstanding seeks at the same time. If you want to add a new seek you must clear your currently active seeks. Clear your seeks?"))
        label.set_width_chars(80)
        label.props.xalign = 0
        label.set_line_wrap(True)
        def response_cb (infobar, response, message):
            if response == gtk.RESPONSE_YES:
                self.connection.client.run_command("unseek")
            message.dismiss()
            return False
        message = InfoBarMessage(gtk.MESSAGE_QUESTION, label, response_cb)
        message.add_button(InfoBarMessageButton(gtk.STOCK_YES, gtk.RESPONSE_YES))
        message.add_button(InfoBarMessageButton(gtk.STOCK_NO, gtk.RESPONSE_NO))
        self.messages.append(message)
        self.infobar.push_message(message)
    
    @glock.glocked
    def onPlayGameCreated (self, bm, board):
        for message in self.messages:
            message.dismiss()
        del self.messages[:]
        return False
    
    @glock.glocked
    def matchDeclined (self, bm, player):
        text = _(" has declined your offer for a match.")
        content = self.get_infobarmessage_content(player, text)
        def response_cb (infobar, response, message):
            message.dismiss()
            return False
        message = InfoBarMessage(gtk.MESSAGE_INFO, content, response_cb)
        message.add_button(InfoBarMessageButton(gtk.STOCK_CLOSE,
                                                gtk.RESPONSE_CANCEL))
        self.messages.append(message)
        self.infobar.push_message(message)
    
    @glock.glocked
    def on_seek_updated (self, glm, message_text):
        if "manual accept" in message_text:
            message_text.replace("to manual accept", _("to manual accept"))
        elif "automatic accept" in message_text:
            message_text.replace("to automatic accept", _("to automatic accept"))
        if "rating range now" in message_text:
            message_text.replace("rating range now", _("rating range now"))
        label = gtk.Label(_("Seek updated") + ": " + message_text)
        def response_cb (infobar, response, message):
            message.dismiss()
            return False
        message = InfoBarMessage(gtk.MESSAGE_INFO, label, response_cb)
        message.add_button(InfoBarMessageButton(gtk.STOCK_CLOSE,
                                                gtk.RESPONSE_CANCEL))
        self.messages.append(message)
        self.infobar.push_message(message)
    
    @glock.glocked
    def our_seeks_removed (self, glm):
        label = gtk.Label(_("Your seeks have been removed"))
        def response_cb (infobar, response, message):
            message.dismiss()
            return False
        message = InfoBarMessage(gtk.MESSAGE_INFO, label, response_cb)
        message.add_button(InfoBarMessageButton(gtk.STOCK_CLOSE,
                                                gtk.RESPONSE_CANCEL))
        self.messages.append(message)
        self.infobar.push_message(message)
        
    def _connect_to_player_changes (self, player):
        for rt in (TYPE_BLITZ, TYPE_LIGHTNING):
            player.ratings[rt].connect("notify::elo",
                self._replace_notification_message, player)
        player.connect("notify::titles",
                       self._replace_notification_message, player)
        
    @glock.glocked
    def _replace_notification_message (self, obj, prop, player):
        log.debug("_replace_notification_message: %s %s" % (repr(obj), repr(player)))
        for message in self.messages:
            if isinstance(message, PlayerNotificationMessage) and \
                    message.player == player:
                message.update_content(
                    self.get_infobarmessage_content(player, message.text))
        return False
    
    def _add_notification_message (self, player, text):
        content = self.get_infobarmessage_content(player, text)
        def response_cb (infobar, response, message):
            message.dismiss()
#             self.messages.remove(message)
            return False
        message = PlayerNotificationMessage(gtk.MESSAGE_INFO, content,
                                            response_cb, player, text)
        message.add_button(InfoBarMessageButton(gtk.STOCK_CLOSE,
                                                gtk.RESPONSE_CANCEL))
        self.messages.append(message)
        self.infobar.push_message(message)
    
    @glock.glocked
    def onArrivalNotification (self, cm, player):
        self._add_notification_message(player, _(" has arrived"))
        if player not in self.players:
            self.players.append(player)
            self._connect_to_player_changes(player)
    
    @glock.glocked
    def onDepartedNotification (self, cm, player):
        self._add_notification_message(player, _(" has departed"))

    @glock.glocked
    def user_from_notify_list_is_present (self, player):
        self._add_notification_message(player, _(" is present"))
        if player not in self.players:
            self.players.append(player)
            self._connect_to_player_changes(player)
    
############################################################################
# Initialize connects for createBoard and createObsBoard                   #
############################################################################

class CreatedBoards (Section):

    def __init__ (self, widgets, connection):
        self.connection = connection
        self.connection.bm.connect("playGameCreated", self.onPlayGameCreated)
        self.connection.bm.connect("obsGameCreated", self.onObserveGameCreated)

    def onPlayGameCreated (self, bm, ficsgame):
        log.debug("ICLounge.onPlayGameCreated: %s" % ficsgame)
        if ficsgame.board.wms == 0 and ficsgame.board.bms == 0:
            timemodel = None
        else:
            timemodel = TimeModel (ficsgame.board.wms/1000., ficsgame.inc,
                bsecs=ficsgame.board.bms/1000., minutes=ficsgame.minutes)
        gamemodel = ICGameModel (self.connection, ficsgame, timemodel)
        gamemodel.connect("game_started", lambda gamemodel:
                     self.connection.bm.onGameModelStarted(ficsgame.gameno))
        
        wplayer, bplayer = ficsgame.wplayer, ficsgame.bplayer
        
        # We start
        if wplayer.name.lower() == self.connection.getUsername().lower():
            player0tup = (LOCAL, Human, (WHITE, wplayer.long_name(), wplayer.name,
                          wplayer.getRatingForCurrentGame()), wplayer.long_name())
            player1tup = (REMOTE, ICPlayer, (gamemodel, bplayer.name,
                ficsgame.gameno, BLACK, bplayer.long_name(),
                bplayer.getRatingForCurrentGame()), bplayer.long_name())
        
        # She starts
        else:
            player1tup = (LOCAL, Human, (BLACK, bplayer.long_name(), bplayer.name,
                          bplayer.getRatingForCurrentGame()), bplayer.long_name())
            # If the remote player is WHITE, we need to init her right now, so
            # we can catch fast made moves. Sorry lazy loading.
            player0 = ICPlayer(gamemodel, wplayer.name, ficsgame.gameno, WHITE,
                               wplayer.long_name(), wplayer.getRatingForCurrentGame())
            player0tup = (REMOTE, lambda:player0, (), wplayer.long_name())
        
        if not ficsgame.board.fen:
            ionest.generalStart(gamemodel, player0tup, player1tup)
        else:
            ionest.generalStart(gamemodel, player0tup, player1tup,
                                (StringIO(ficsgame.board.fen), fen, 0, -1))

    def onObserveGameCreated (self, bm, ficsgame):
        log.debug("ICLounge.onObserveGameCreated: %s" % ficsgame)
        if ficsgame.board.wms == 0 and ficsgame.board.bms == 0:
            timemodel = None
        else:
            timemodel = TimeModel (ficsgame.board.wms/1000., ficsgame.inc,
                bsecs=ficsgame.board.bms/1000., minutes=ficsgame.minutes)
        gamemodel = ICGameModel (self.connection, ficsgame, timemodel)
        gamemodel.connect("game_started", lambda gamemodel:
                     self.connection.bm.onGameModelStarted(ficsgame.gameno))
        
        # The players need to start listening for moves IN this method if they
        # want to be noticed of all moves the FICS server sends us from now on
        wplayer, bplayer = ficsgame.wplayer, ficsgame.bplayer
        player0 = ICPlayer(gamemodel, wplayer.name, ficsgame.gameno,
                           WHITE, wplayer.long_name(), wplayer.getRatingForCurrentGame())
        player1 = ICPlayer(gamemodel, bplayer.name, ficsgame.gameno,
                           BLACK, bplayer.long_name(), bplayer.getRatingForCurrentGame())
        
        player0tup = (REMOTE, lambda:player0, (), wplayer.long_name())
        player1tup = (REMOTE, lambda:player1, (), bplayer.long_name())
        
        ionest.generalStart(gamemodel, player0tup, player1tup,
                            (StringIO(ficsgame.board.pgn), pgn, 0, -1))

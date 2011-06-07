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
    
    def __init__ (self, c):
        GObject.__init__(self)
        self.connection = c
        self.widgets = w = uistuff.GladeWidgets("fics_lounge.glade")
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
        self.connection.connect("error", lambda connection: self.close())
        
        if self.connection.isRegistred():
            numtimes = conf.get("numberOfTimesLoggedInAsRegisteredUser", 0) + 1
            conf.set("numberOfTimesLoggedInAsRegisteredUser", numtimes)

        global sections
        sections = (
            VariousSection(w,c),
            UserInfoSection(w,c),
            NewsSection(w,c),

            SeekTabSection(w,c, self.infobar),
            SeekGraphSection(w,c),
            PlayerTabSection(w,c),
            GameTabSection(w,c),
            AdjournedTabSection(w,c),

            ChatWindow(w,c),
            #ConsoleWindow(w,c),

            SeekChallengeSection(w,c),
            
            # This is not really a section. It handles server messages which
            # don't correspond to a running game
            Messages(w,c, self.infobar),
            
            # This is not really a section. Merely a pair of BoardManager connects
            # which takes care of ionest and stuff when a new game is started or
            # observed
            CreatedBoards(w,c)
        )

    def show (self):
        self.widgets["fics_lounge"].show()

    def present (self):
        self.widgets["fics_lounge"].present()

    def close (self):
        if self.widgets != None:
            self.widgets["fics_lounge"].hide()
        global sections
        if 'sections' in globals() and sections != None:
            for i in range(len(sections)):
                if hasattr(sections[i], "__del__"):
                    sections[i].__del__()
        sections = None
        if self.connection != None:
            self.connection.close()
        self.connection = None
        self.widgets = None

################################################################################
# Initialize Sections                                                          #
################################################################################

class Section:
    pass

############################################################################
# Initialize Various smaller sections                                      #
############################################################################

class VariousSection(Section):
    def __init__ (self, widgets, connection):
        #sizeGroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        #sizeGroup.add_widget(widgets["show_chat_label"])
        #sizeGroup.add_widget(widgets["show_console_label"])
        #sizeGroup.add_widget(widgets["log_off_label"])

        connection.em.connect("onCommandNotFound", lambda em, cmd:
                log.error("Fics answered '%s': Command not found" % cmd))

############################################################################
# Initialize User Information Section                                      #
############################################################################

class UserInfoSection(Section):

    def __init__ (self, widgets, connection):
        self.widgets = widgets
        self.connection = connection
        self.pinger = None

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
            pingLabel = gtk.Label(_("Connecting")+"...")
            pingLabel.props.xalign = 0
            self.pinger = pinger = Pinger("freechess.org")
            def callback (pinger, pingtime):
                if type(pingtime) == str:
                    pingLabel.set_text(pingtime)
                elif pingtime == -1:
                    pingLabel.set_text(_("Unknown"))
                else: pingLabel.set_text("%.0f ms" % pingtime)
            pinger.connect("recieved", callback)
            pinger.connect("error", callback)
            pinger.start()
            table.attach(pingLabel, 1, 6, row, row+1)
            row += 1

            if not self.connection.isRegistred():
                vbox = gtk.VBox()
                table.attach(vbox, 0, 6, row, row+1)
                label0 = gtk.Label(_("You are currently logged in as a guest.\nA guest is not able to play rated games, and thus the offer of games will be smaller."))
                label0.props.xalign = 0
                label0.props.wrap = True
                label0.props.width_request = 300
                vbox.add(label0)
                eventbox = uistuff.initLabelLinks(_("Register now"),
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
        self.store = gtk.ListStore(str, gtk.gdk.Pixbuf, str, int, str, str, str, float, str, str)
        self.tv.set_model(gtk.TreeModelSort(self.store))
        self.addColumns (self.tv, "gameno", "", _("Name"), _("Rating"),
                         _("Rated"), _("Type"), _("Clock"), "gametime",
                         "textcolor", "tooltip", hide=[0,7,8,9], pix=[1] )
        self.tv.set_search_column(2)
        self.tv.set_tooltip_column(9,)
        for i in range(1, 7):
            self.tv.get_model().set_sort_func(i, self.compareFunction, i)
        try:
            self.tv.set_search_position_func(self.lowLeftSearchPosFunc)
        except AttributeError:
            # Unknow signal name is raised by gtk < 2.10
            pass
        for n in range(1, 6):
            column = self.tv.get_column(n)
            for cellrenderer in column.get_cell_renderers():
                column.add_attribute(cellrenderer, "foreground", 8)
        self.selection = self.tv.get_selection()
        self.lastSeekSelected = None
        self.selection.set_select_function(self.selectFunction, full=True)
        self.selection.connect("changed", self.onSelectionChanged)
        self.widgets["clearSeeksButton"].connect("clicked", self.onClearSeeksClicked)
        self.widgets["acceptButton"].connect("clicked", self.onAcceptClicked)
        self.widgets["declineButton"].connect("clicked", self.onDeclineClicked)
        self.tv.connect("row-activated", self.row_activated)
        
        self.connection.glm.connect("addSeek", lambda glm, seek:
                self.listPublisher.put((self.onAddSeek, seek)) )
        self.connection.glm.connect("removeSeek", lambda glm, gameno:
                self.listPublisher.put((self.onRemoveSeek, gameno)) )
        self.connection.om.connect("onChallengeAdd", lambda om, index, match:
                self.listPublisher.put((self.onChallengeAdd, index, match)) )
        self.connection.om.connect("onChallengeRemove", lambda om, index:
                self.listPublisher.put((self.onChallengeRemove, index)) )
        self.connection.glm.connect("clearSeeks", lambda glm:
                self.listPublisher.put((self.onClearSeeks,)) )
        self.connection.bm.connect("playGameCreated", lambda bm, game:
                self.listPublisher.put((self.onPlayingGame,)) )
        self.connection.bm.connect("curGameEnded", lambda bm, game:
                self.listPublisher.put((self.onCurGameEnded,)) )
        
    def selectFunction (self, selection, model, path, is_selected):
        if model[path][8] == "grey": return False
        else: return True
    
    def __isAChallengeOrOurSeek (self, row):
        gameno = row[0]
        textcolor = row[8]
        if (gameno is not None and gameno.startswith("C")) or (textcolor == "grey"):
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
        elif column is 6:
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
        time = _("%(min)s min") % {'min': seek["t"]}
        if seek["i"] != "0":
            time += _(" + %(sec)s sec") % {'sec': seek["i"]}
        rated = seek["r"] == "u" and _("Unrated") or _("Rated")
        pix = seek["manual"] and self.manSeekPix or self.seekPix
        try:
            ficsplayer = self.connection.playersonline[FICSPlayer(seek["w"])]
        except KeyError:
            return
        nametitle = ficsplayer.name + ficsplayer.getTitles()
        textcolor = "grey" if ficsplayer.name == self.connection.getUsername() \
                           else "black"
        is_rated = False if seek["r"] == "u" else True
        is_computer = ficsplayer.isComputer()
        tooltiptext = SeekGraphSection.getSeekTooltipText(nametitle,
            seek["rt"], is_computer, is_rated, seek["manual"], seek["gametype"],
            seek["t"], seek["i"], rmin=seek["rmin"], rmax=seek["rmax"])
        seek_ = [seek["gameno"], pix, nametitle, int(seek["rt"]), rated,
            seek["gametype"].display_text, time,
            float(seek["t"] + "." + seek["i"]), textcolor, tooltiptext]

        if textcolor == "grey":
            ti = self.store.prepend(seek_)
            self.tv.scroll_to_cell(self.store.get_path(ti))
            self.widgets["clearSeeksButton"].set_sensitive(True)
        else:
            ti = self.store.append(seek_)
        self.seeks [seek["gameno"]] = ti
        self.__updateActiveSeeksLabel()
        
    def onRemoveSeek (self, gameno):
        if not gameno in self.seeks:
            # We ignore removes we haven't added, as it seams fics sends a
            # lot of removes for games it has never told us about
            return
        treeiter = self.seeks [gameno]
        if not self.store.iter_is_valid(treeiter):
            return
        self.store.remove (treeiter)
        del self.seeks[gameno]
        self.__updateActiveSeeksLabel()
    
    def onChallengeAdd (self, index, match):
        SoundTab.playAction("aPlayerChecks")
        time = _("%(min)s min") % {'min': match["t"]}
        if match["i"] != "0":
            time += _(" + %(sec)s sec") % {'sec': match["i"]}
        rated = match["r"] == "u" and _("Unrated") or _("Rated")
        try:
            ficsplayer = self.connection.playersonline[FICSPlayer(match["w"])]
        except KeyError:
            return
        nametitle = ficsplayer.name + ficsplayer.getTitles()
        is_rated = False if match["r"] == "u" else True
        is_manual = False
        
        # TODO: differentiate between challenges and manual-seek-accepts
        # (wait until seeks are comparable FICSSeek objects to do this)
        content = gtk.HBox()
        icon = gtk.Image()
        icon.set_from_pixbuf(
            ficsplayer.getIcon(size=22, gametype=match["gametype"]))
        content.pack_start(icon, expand=False, fill=False, padding=4)
        label = gtk.Label()
        label.set_markup(ficsplayer.getMarkup(gametype=match["gametype"]))
        content.pack_start(label, expand=False, fill=False)
        if match["is_adjourned"]:
            text = _(" would like to resume your adjourned %s %s game of %s")
        else:
            text = _(" challenges you to a %s %s game of %s")
        label = gtk.Label(text % (rated, match["gametype"].display_text, time))
        content.pack_start(label, expand=False, fill=False)
        def callback (infobar, response):
            if response == gtk.RESPONSE_ACCEPT:
                self.connection.om.acceptIndex(index)
            elif response == gtk.RESPONSE_NO:
                self.connection.om.declineIndex(index)
        message = InfoBarMessage(gtk.MESSAGE_INFO, content, callback,
                                 (_("Accept"), gtk.RESPONSE_ACCEPT),
                                 (_("Decline"), gtk.RESPONSE_NO))
        self.messages[index] = message
        self.infobar.push_message(message)
        
        tooltiptext = SeekGraphSection.getSeekTooltipText(nametitle,
            match["rt"], ficsplayer.isComputer(), is_rated, is_manual,
            match["gametype"], match["t"], match["i"])
        ti = self.store.prepend (["C"+index, self.chaPix, nametitle,
            int(match["rt"]), rated, match["gametype"].display_text, time,
            float(match["t"] + "." + match["i"]), "black", tooltiptext])
        self.challenges[index] = ti
        self.__updateActiveSeeksLabel()
        self.widgets["seektreeview"].scroll_to_cell(self.store.get_path(ti))

    def onChallengeRemove (self, index):
        if not index in self.challenges: return
        if index in self.messages:
            self.messages[index].dismiss()
            del self.messages[index]
        ti = self.challenges[index]
        if not self.store.iter_is_valid(ti): return
        self.store.remove(ti)
        del self.challenges[index]
        self.__updateActiveSeeksLabel()

    def onClearSeeks (self):
        self.store.clear()
        self.seeks = {}
        self.__updateActiveSeeksLabel()

    def onAcceptClicked (self, button):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        index = model.get_value(iter, 0)
        if index.startswith("C"):
            index = index[1:]
            self.connection.om.acceptIndex(index)
        else:
            self.connection.om.playIndex(index)
        if index in self.messages:
            self.messages[index].dismiss()
            del self.messages[index]

    def onDeclineClicked (self, button):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        index = model.get_value(iter, 0)
        if index.startswith("C"):
            index = index[1:]
        self.connection.om.declineIndex(index)
        if index in self.messages:
            self.messages[index].dismiss()
            del self.messages[index]
        
    def onClearSeeksClicked (self, button):
        print >> self.connection.client, "unseek"
        self.widgets["clearSeeksButton"].set_sensitive(False)
    
    def row_activated (self, treeview, path, view_column):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        index = model.get_value(iter, 0)
        if index != self.lastSeekSelected: return
        if path != model.get_path(iter): return
        self.onAcceptClicked(None)

    def onSelectionChanged (self, selection):
        model, iter = self.widgets["seektreeview"].get_selection().get_selected()
        if iter == None: return
        self.lastSeekSelected = model.get_value(iter, 0)
    
    def _clear_messages (self):
        for message in self.messages.values():
            message.dismiss()
        self.messages = {}
    
    def onPlayingGame (self):
        self._clear_messages()
        self.widgets["seekListContent"].set_sensitive(False)
        self.widgets["clearSeeksButton"].set_sensitive(False)
        self.store.clear()
        self.__updateActiveSeeksLabel()

    def onCurGameEnded (self):
        self.widgets["seekListContent"].set_sensitive(True)
        self.connection.glm.refreshSeeks()

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

        self.connection.glm.connect("addSeek", lambda glm, seek:
                self.listPublisher.put((self.onSeekAdd, seek)) )

        self.connection.glm.connect("removeSeek", lambda glm, gameno:
                self.listPublisher.put((self.onSeekRemove, gameno)) )

        self.connection.glm.connect("clearSeeks", lambda glm:
                self.listPublisher.put((self.onSeekClear,)) )

        self.connection.bm.connect("playGameCreated", lambda bm, game:
                self.listPublisher.put((self.onPlayingGame,)) )

        self.connection.bm.connect("curGameEnded", lambda bm, game:
                self.listPublisher.put((self.onCurGameEnded,)) )

    def onSpotClicked (self, graph, name):
        self.connection.bm.play(name)

    @classmethod
    def getSeekTooltipText (cls, name, rating, is_computer, is_rated, is_manual,
                            gametype, min, gain, rmin=0, rmax=9999):
        if int(rating) == 0:
            rating = _("Unrated")
        text = "%s (%s)" % (name, rating)
        if is_computer:  # remove from testing/ficsmanagers.py as well when removing this
            text += " (%s)" % _("Computer Player")
        rated = _("Rated") if is_rated else _("Unrated")
        text += "\n%s %s" % (rated, gametype.display_text)
        text += "\n" + _("%(min)s min + %(sec)s sec") % {'min': min, 'sec': gain}
        rrtext = SeekChallengeSection.getRatingRangeDisplayText(rmin, rmax)
        if rrtext:
            text += "\n%s: %s" % (_("Opponent Rating"), rrtext)
        if is_manual:
            text += "\n%s" % _("Manual Accept")
        return text
    
    def onSeekAdd (self, seek):
        x = XLOCATION (float(seek["t"]) + float(seek["i"]) * GAME_LENGTH/60.)
        y = seek["rt"].isdigit() and YLOCATION(float(seek["rt"])) or 0
        type = seek["r"] == "u" and 1 or 0
        try:
            ficsplayer = self.connection.playersonline[FICSPlayer(seek["w"])]
        except KeyError:
            return
        nametitle = ficsplayer.name + ficsplayer.getTitles()
        is_rated = False if seek["r"] == "u" else True
        text = self.getSeekTooltipText(nametitle, seek["rt"], seek["cp"],
            is_rated, seek["manual"], seek["gametype"], seek["t"], seek["i"],
            rmin=seek["rmin"], rmax=seek["rmax"])
        self.graph.addSpot(seek["gameno"], text, x, y, type)

    def onSeekRemove (self, gameno):
        self.graph.removeSpot(gameno)

    def onSeekClear (self):
        self.graph.clearSpots()

    def onPlayingGame (self):
        self.widgets["seekGraphContent"].set_sensitive(False)
        self.graph.clearSpots()

    def onCurGameEnded (self):
        self.widgets["seekGraphContent"].set_sensitive(True)

########################################################################
# Initialize Players List                                              #
########################################################################

PLAYERADDED, PLAYERCHANGED, PLAYERREMOVED = range(3)

class PlayerTabSection (ParrentListSection):
    
    widgets = []
    
    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)

        PlayerTabSection.widgets = widgets
        self.connection = connection
        
        self.players = {}
        
        self.tv = widgets["playertreeview"]
        self.store = gtk.ListStore(gtk.gdk.Pixbuf, str, int, int, int, str)
        self.tv.set_model(gtk.TreeModelSort(self.store))
        self.addColumns(self.tv, "", _("Name"), _("Blitz"), _("Standard"), _("Lightning"), _("Status"), pix=[0])
        self.tv.get_column(0).set_sort_column_id(0)
        self.tv.get_model().set_sort_func(0, self.pixCompareFunction, 0)
        try:
            self.tv.set_search_position_func(self.lowLeftSearchPosFunc)
        except AttributeError:
            # Unknow signal name is raised by gtk < 2.10
            pass

        connection.playersonline.connect("FICSPlayerEntered", self.onPlayerAdded)
        connection.playersonline.connect("FICSPlayerChanged", self.onPlayerChanged)
        connection.playersonline.connect("FICSPlayerExited", self.onPlayerRemoved)

        widgets["private_chat_button"].connect("clicked", self.onPrivateChatClicked)
        widgets["private_chat_button"].set_sensitive(False)
        widgets["observe_button"].connect("clicked", self.onObserveClicked)
        widgets["observe_button"].set_sensitive(False)
        glock.glock_connect_after(self.tv.get_selection(), "changed", self.onSelectionChanged)

        self.playerUpdates = Queue.Queue()
        def cb ():
            self.listPublisher.put((self.processPlayerUpdates,))
            return True
        gobject.timeout_add(1000 * 5, cb)
        
    def getColumnValues (self, player):
        icon = player.getIcon()
        nametitle = player.name + player.getTitles()
        blitz = player.getRating(TYPE_BLITZ)
        if blitz: blitz = blitz.elo
        else: blitz = 0
        std = player.getRating(TYPE_STANDARD)
        if std: std = std.elo
        else: std = 0
        light = player.getRating(TYPE_LIGHTNING)
        if light: light = light.elo
        else: light = 0
        status = ""
        if player.status == IC_STATUS_AVAILABLE:
            status = _("Available")
        elif player.status == IC_STATUS_PLAYING:
            status = _("Playing")
        elif player.status == IC_STATUS_IDLE:
            status = _("Idle")
        elif player.status == IC_STATUS_EXAMINING:
            status = _("Examining")
        elif player.status == IC_STATUS_NOT_AVAILABLE:
            status = _("Not Available")
        elif player.status == IC_STATUS_RUNNING_SIMUL_MATCH:
            status = _("Running Simul Match")
        elif player.status == IC_STATUS_IN_TOURNAMENT:
            status = _("In Tournament")
        return icon, nametitle, blitz, std, light, status

    def processPlayerUpdates (self):
        while True:
            try:
                playerupdate = self.playerUpdates.get_nowait()
            except Queue.Empty:
                break
            else:
                player, updatetype = playerupdate
                if updatetype in (PLAYERADDED, PLAYERCHANGED):
                    icon, nametitle, blitz, std, light, status = self.getColumnValues(player)
                    if player.name in self.players:
                        ti = self.players[player.name]
                        if self.store.iter_is_valid(ti):
                            self.store.set(ti, 0, icon, 1, nametitle, 2, blitz, 3, std, 4, light, 5, status)
                        else:
                            del self.players[player.name]
                    else:  # add him
                        ti = self.store.append([icon, nametitle, blitz, std, light, status])
                        self.players[player.name] = ti                        
                elif updatetype == PLAYERREMOVED and player.name in self.players:
                    ti = self.players[player.name]
                    if self.store.iter_is_valid(ti):
                        self.store.remove(ti)
                    del self.players[player.name]
        
        count = len(self.players)
        self.widgets["playersOnlineLabel"].set_text(_("Players: %d") % count)

    def onPlayerAdded (self, ficspo, player):
        self.playerUpdates.put((player, PLAYERADDED))
        
    def onPlayerRemoved (self, ficspo, player):
        self.playerUpdates.put((player, PLAYERREMOVED))

    def onPlayerChanged (self, ficspo, player):
        self.playerUpdates.put((player, PLAYERCHANGED))
    
    @classmethod
    def getSelectedPlayerName (cls):
        model, iter = cls.widgets["playertreeview"].get_selection().get_selected()
        if iter == None: return None
        playername = model.get_value(iter, 1)
        m = re.match("(\w+)\W*", playername)
        playername = m.groups()[0]
        return playername
    
    def onPrivateChatClicked (self, button):
        playername = self.getSelectedPlayerName()
        if playername is None: return
        for section in sections:
            if isinstance(section, ChatWindow):
                section.openChatWithPlayer(playername)
                #TODO: isadmin og type
    
    def onObserveClicked (self, button):
        player = self.getSelectedPlayerName()
        if player is None: return
        try:
            player = self.connection.playersonline[FICSPlayer(player)]
        except KeyError:
            player = None
        if player is not None and player.game is not None:
            self.connection.bm.observe(player.game.gameno)
        
    def onSelectionChanged (self, selection):
        player = self.getSelectedPlayerName()
        if player is not None:
            try:
                player = self.connection.playersonline[FICSPlayer(player)]
            except KeyError:
                player = None
        self.widgets["private_chat_button"].set_sensitive(player is not None)
        self.widgets["observe_button"].set_sensitive(
            player is not None and player.isObservable())
        self.widgets["challengeButton"].set_sensitive(
            player is not None and player.isAvailableForGame())
        
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
        self.store = gtk.ListStore(int, gtk.gdk.Pixbuf, str, int, str, int, str, int)
        self.tv.set_model(gtk.TreeModelSort(self.store))
        self.tv.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.addColumns (
                self.tv, "GameNo", "", _("White Player"), _("Rating"),
                _("Black Player"), _("Rating"),
                _("Game Type"), "Time", hide=[0,7], pix=[1] )
        self.tv.get_column(0).set_sort_column_id(0)
        self.tv.get_model().set_sort_func(0, self.pixCompareFunction, 1)

        self.selection = self.tv.get_selection()
        self.selection.connect("changed", self.onSelectionChanged)
        self.onSelectionChanged(self.selection)

        def typeCompareFunction (treemodel, iter0, iter1):
            return cmp (treemodel.get_value(iter0, 7),
                        treemodel.get_value(iter1, 7))
        self.tv.get_model().set_sort_func(6, typeCompareFunction)

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

        self.connection.glm.connect("addGame", lambda glm, ficsgame:
                self.listPublisher.put((self.onGameAdd, ficsgame)) )
        self.connection.glm.connect("removeGame", lambda glm, ficsgame:
                self.listPublisher.put((self.onGameRemove, ficsgame.gameno)) )
        self.connection.bm.connect("wasPrivate", lambda bm, game:
                self.listPublisher.put((self.onWasPrivate, game)) )
        self.widgets["observeButton"].connect ("clicked", self.onObserveClicked)
        self.tv.connect("row-activated", self.onObserveClicked)
        self.connection.bm.connect("obsGameCreated", lambda bm, ficsgame:
                self.listPublisher.put((self.onGameObserved, ficsgame)) )
        self.connection.bm.connect("obsGameUnobserved", lambda bm, gameno:
                self.listPublisher.put((self.onGameUnobserved, gameno)) )

    def onSelectionChanged (self, selection):
        model, paths = selection.get_selected_rows()
        a_selected_game_is_observable = False
        for path in paths:
            rowiter = model.get_iter(path)
            gameno = model.get_value(rowiter, 0)
            try:
                game = self.connection.gamesinprogress[int(gameno)]
            except KeyError: continue
            if not game.private:
                a_selected_game_is_observable = True
                break        
        self.widgets["observeButton"].set_sensitive(a_selected_game_is_observable)

    def onGameAdd (self, ficsgame):
        gametype = ficsgame.game_type.display_text
        
        if ficsgame.min != None:
            length = ficsgame.min*60 + ficsgame.inc*40
        elif ficsgame.game_type.rating_type == TYPE_LIGHTNING:
            length = 100
        elif ficsgame.game_type.rating_type == TYPE_BLITZ:
            length = 9*60
        elif ficsgame.game_type.rating_type == TYPE_STANDARD:
            length = 15*60
        else:
            length = 0
        
        if ficsgame.private == True:
            gametype += ", " + _("Private")
        
#        print "GameTab.onGameAdd():"
#        print "gameno = %s, wname = %s, wrating = %s, bname = %s, brating = %s (type=%s), type = %s (type=%s), length = %s" \
#            % (str(ficsgame.gameno), str(ficsgame.wplayer.name + ficsgame.wplayer.getTitles()), str(wrating),
#               str(ficsgame.bplayer.name + ficsgame.bplayer.getTitles()), str(brating), type(brating), str(gametype), type(gametype), str(length))
        ti = self.store.append ([ficsgame.gameno, self.clearpix,
                                 ficsgame.wplayer.name + ficsgame.wplayer.getTitles(),
                                 ficsgame.wplayer.getRatingForCurrentGame() or 0,
                                 ficsgame.bplayer.name + ficsgame.bplayer.getTitles(),
                                 ficsgame.bplayer.getRatingForCurrentGame() or 0, gametype, length])
        self.games[ficsgame.gameno] = ti
        count = len(self.games)
        self.widgets["gamesRunningLabel"].set_text(_("Games running: %d") % count)

    def onWasPrivate (self, gameno):
        # When observable games were added to the list later than the latest
        # full send, private information will not be known.
        model, paths = self.tv.get_selection().get_selected_rows()
        for path in paths:
            rowiter = model.get_iter(path)
            if gameno == model.get_value(rowiter, 0):
                gametype = model.get_value(rowiter, 6)
                if not _("Private") in gametype:
                    gametype += ", " + _("Private")
                    childmodel = model.get_model()
                    childrowiter = model.convert_iter_to_child_iter(None, rowiter)
                    childmodel.set_value(childrowiter, 6, gametype)
                break

    def onGameRemove (self, gameno):
        if not gameno in self.games:
            return
        ti = self.games[gameno]
        if not self.store.iter_is_valid(ti):
            return
        self.store.remove (ti)
        del self.games[gameno]
        count = len(self.games)
        self.widgets["gamesRunningLabel"].set_text(_("Games running: %d") % count)

    def onObserveClicked (self, widget, *args):
        model, paths = self.tv.get_selection().get_selected_rows()
        for path in paths:
            rowiter = model.get_iter(path)
            gameno = model.get_value(rowiter, 0)
            self.connection.bm.observe(gameno)

    def onGameObserved (self, ficsgame):
        threeiter = self.games[ficsgame.gameno]
        self.store.set_value (threeiter, 1, self.recpix)

    def onGameUnobserved (self, gameno):
        if gameno in self.games:
            threeiter = self.games[gameno]
            self.store.set_value(threeiter, 1, self.clearpix)

########################################################################
# Initialize Adjourned List                                            #
########################################################################

class AdjournedTabSection (ParrentListSection):

    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)
        self.connection = connection
        self.widgets = widgets
        self.opponents = {}

        self.wpix = load_icon(16, "stock_draw-rounded-square-unfilled", "computer")
        self.bpix = load_icon(16, "stock_draw-rounded-square", "computer")

        self.tv = widgets["adjournedtreeview"]
        self.store = gtk.ListStore(gtk.gdk.Pixbuf, str, str, str, str)
        self.tv.set_model(gtk.TreeModelSort(self.store))
        self.addColumns (self.tv, _("Your Color"), _("Opponent"),
                                  _("Is Online"), _("Length"), _("Date/Time"), pix=[0])
        self.selection = self.tv.get_selection()
        self.selection.connect("changed", self.onSelectionChanged)
        self.onSelectionChanged(self.selection)

        self.connection.adm.connect("onAdjournmentsList", lambda glm, adjournments:
                self.listPublisher.put((self.onAdjournmentsList, adjournments)) )
        self.connection.adm.queryAdjournments()

        self.connection.bm.connect("curGameEnded", lambda bm, game:
                self.listPublisher.put((self.onCurGameEnded, game.result)))

        widgets["resignButton"].connect("clicked", self.onResignButtonClicked)
        widgets["abortButton"].connect("clicked", self.onAbortButtonClicked)
        widgets["drawButton"].connect("clicked", self.onDrawButtonClicked)
        widgets["resumeButton"].connect("clicked", self.onResumeButtonClicked)
        widgets["previewButton"].connect("clicked", self.onPreviewButtonClicked)
        self.tv.connect("row-activated", lambda *args: self.onPreviewButtonClicked(None))
        self.connection.adm.connect("onGamePreview", lambda adm, board:
            self.listPublisher.put((self.onGamePreview, board)))

    def onSelectionChanged (self, selection):
        model, iter = selection.get_selected()
        a_row_is_selected = False
        if iter != None:
            a_row_is_selected = True
        for button in ("resignButton", "abortButton", "drawButton", "resumeButton",
                       "previewButton"):
            self.widgets[button].set_sensitive(a_row_is_selected)

    def onAdjournmentsList (self, adjournments):
        self.store.clear()
        self.opponents.clear()
        
        for adjourn in adjournments:
            if adjourn["opponent"].lower() in self.opponents:
                continue
            pix = (self.wpix, self.bpix)[adjourn["color"]]
            opstatus = adjourn["online"] and _("Online") or _("Offline")
            ti = self.store.append ([pix, adjourn["opponent"],
                                     opstatus, adjourn["length"], adjourn["time"]])
            self.opponents[adjourn["opponent"].lower()] = ti

    def onCurGameEnded (self, result):
        if result == ADJOURNED:
            self.store.clear()
            self.opponents.clear()
            self.connection.adm.queryAdjournments()

    def onResignButtonClicked (self, button):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        opponent = model.get_value(iter, 1)
        self.connection.adm.resign(opponent)
    
    def onDrawButtonClicked (self, button):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        opponent = model.get_value(iter, 1)
        self.connection.adm.draw(opponent)
    
    def onAbortButtonClicked (self, button):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        opponent = model.get_value(iter, 1)
        self.connection.adm.abort(opponent)
    
    def onResumeButtonClicked (self, button):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        opponent = model.get_value(iter, 1)
        self.connection.adm.resume(opponent)
    
    def onPreviewButtonClicked (self, button):
        model, iter = self.tv.get_selection().get_selected()
        if iter == None: return
        opponent = model.get_value(iter, 1)
        self.connection.adm.queryMoves(opponent)

    def onGamePreview (self, ficsgame):
        log.debug("ICLounge.onGamePreview: %s\n" % ficsgame)
        if ficsgame.board.wms == 0 and ficsgame.board.bms == 0:
            timemodel = None
        else:
            timemodel = TimeModel(ficsgame.board.wms/1000., ficsgame.inc,
                                  bsecs=ficsgame.board.bms/1000.)
        gamemodel = ICGameModel(self.connection, ficsgame, timemodel)
        
        # The players need to start listening for moves IN this method if they
        # want to be noticed of all moves the FICS server sends us from now on
        player0 = ICPlayer(gamemodel, ficsgame.wplayer.name, -1, WHITE,
            icrating=ficsgame.wplayer.getRating(ficsgame.game_type.rating_type).elo)
        player1 = ICPlayer(gamemodel, ficsgame.bplayer.name, -1, BLACK,
            icrating=ficsgame.bplayer.getRating(ficsgame.game_type.rating_type).elo)
        
        player0tup = (REMOTE, lambda:player0, (), ficsgame.wplayer.name,
            ficsgame.wplayer.getRating(ficsgame.game_type.rating_type).elo)
        player1tup = (REMOTE, lambda:player1, (), ficsgame.bplayer.name,
            ficsgame.bplayer.getRating(ficsgame.game_type.rating_type).elo)
        
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
        
        seekSelection = self.widgets["seektreeview"].get_selection()
        seekSelection.connect_after("changed", self.onSeekSelectionChanged)
        
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
        playername = PlayerTabSection.getSelectedPlayerName()
        if playername is None: return
        try:
            player = self.connection.playersonline[FICSPlayer(playername)]
        except KeyError:
            return
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
        self.widgets["challengeeImage"].set_from_pixbuf(player.getIcon(size=22))
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
    
    def onSeekSelectionChanged (self, selection):
        model, iter = selection.get_selected()
        a_seek_is_selected = False
        selection_is_challenge = False
        if iter != None:
            a_seek_is_selected = True
            gameno = model.get_value(iter, 0)
            if gameno.startswith("C"):
                selection_is_challenge = True
        self.widgets["acceptButton"].set_sensitive(a_seek_is_selected)
        self.widgets["declineButton"].set_sensitive(selection_is_challenge)
    
    #-------------------------------------------------------- Seek Editor
    
    @staticmethod
    def getRatingRangeDisplayText (rmin=0, rmax=9999):
        assert type(rmin) is type(int()) and rmin >= 0 and rmin <= 9999, rmin
        assert type(rmax) is type(int()) and rmax >= 0 and rmax <= 9999, rmax
        if rmin > 0:
            text = "%d" % rmin
            if rmax == 9999:
                text += "↑"
            else:
                text += "-%d" % rmax
        elif rmax != 9999:
            text = "%d↓" % rmax
        else:
            text = None
        return text
    
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
        
        rrtext = self.getRatingRangeDisplayText(ratingrange[0], ratingrange[1])
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
                      VARIANTS_OTHER: _("Other")}
        ficsvariants = [v for k, v in variants.iteritems() if k in VARIANT_GAME_TYPES]
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
            assert variant in VARIANT_GAME_TYPES, \
                "not a supported FICS variant: \"%s\"" % str(variant)
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

class ConsoleWindow:
    def __init__ (self, widgets, connection):
        pass

############################################################################
# Relay server messages to the user which aren't part of a game            #
############################################################################

class Messages (Section):
    def __init__ (self, widgets, connection, infobar):
        self.connection = connection
        self.infobar = infobar
        self.messages = []
        self.connection.bm.connect("tooManySeeks", self.tooManySeeks)
        self.connection.bm.connect("matchDeclined", self.matchDeclined)
        self.connection.bm.connect("playGameCreated", self.onPlayGameCreated)
        
    @glock.glocked
    def tooManySeeks (self, bm):
        label = gtk.Label(_("You can only have 3 outstanding seeks at the same time. If you want to add a new seek you must clear your currently active seeks. Clear your seeks?"))
        label.set_width_chars(70)
        label.set_line_wrap(True)
        def response_cb (infobar, response):
            if response == gtk.RESPONSE_YES:
                print >> self.connection.client, "unseek"
        message = InfoBarMessage(gtk.MESSAGE_WARNING, label, response_cb,
                                 (gtk.STOCK_YES, gtk.RESPONSE_YES),
                                 (gtk.STOCK_NO, gtk.RESPONSE_NO))
        self.infobar.push_message(message)
        self.messages.append(message)
    
    @glock.glocked
    def onPlayGameCreated (self, bm, board):
        for message in self.messages:
            message.dismiss()
        self.messages = []
        return False
    
    @glock.glocked
    def matchDeclined (self, bm, decliner):
        label = gtk.Label(_("%s has declined your offer for a match") % decliner)
        message = InfoBarMessage(gtk.MESSAGE_INFO, label, None)
        self.infobar.push_message(message)

############################################################################
# Initialize connects for createBoard and createObsBoard                   #
############################################################################

class CreatedBoards (Section):

    def __init__ (self, widgets, connection):
        self.connection = connection
        self.connection.gamesinprogress.connect("FICSPlayGameCreated", self.onPlayGameCreated)
        self.connection.gamesinprogress.connect("FICSObsGameCreated", self.onObserveGameCreated)

    def onPlayGameCreated (self, bm, ficsgame):
        log.debug("ICLounge.onPlayGameCreated: %s\n" % ficsgame)
        if ficsgame.board.wms == 0 and ficsgame.board.bms == 0:
            timemodel = None
        else:
            timemodel = TimeModel (ficsgame.board.wms/1000., ficsgame.inc,
                                   bsecs=ficsgame.board.bms/1000.)
        gamemodel = ICGameModel (self.connection, ficsgame, timemodel)
        gamemodel.connect("game_started", lambda gamemodel:
                     self.connection.bm.onGameModelStarted(ficsgame.gameno))
        
        if ficsgame.wplayer.name.lower() == self.connection.getUsername().lower():
            player0tup = (LOCAL, Human, (WHITE, "", ficsgame.wplayer.name,
                          ficsgame.wplayer.getRatingForCurrentGame()), _("Human"),
                          ficsgame.wplayer.getRatingForCurrentGame(),
                          ficsgame.wplayer.getTitles())
            player1tup = (REMOTE, ICPlayer, (gamemodel, ficsgame.bplayer.name,
                ficsgame.gameno, BLACK, ficsgame.bplayer.getRatingForCurrentGame()),
                ficsgame.bplayer.name, ficsgame.bplayer.getRatingForCurrentGame(),
                ficsgame.bplayer.getTitles())
        else:
            player1tup = (LOCAL, Human, (BLACK, "", ficsgame.bplayer.name,
                          ficsgame.bplayer.getRatingForCurrentGame()), _("Human"),
                          ficsgame.bplayer.getRatingForCurrentGame(),
                          ficsgame.bplayer.getTitles())
            # If the remote player is WHITE, we need to init him right now, so
            # we can catch fast made moves
            player0 = ICPlayer(gamemodel, ficsgame.wplayer.name, ficsgame.gameno, WHITE,
                               icrating=ficsgame.wplayer.getRatingForCurrentGame())
            player0tup = (REMOTE, lambda:player0, (), ficsgame.wplayer.name,
                          ficsgame.wplayer.getRatingForCurrentGame(),
                          ficsgame.wplayer.getTitles())
        
        if not ficsgame.board.fen:
            ionest.generalStart(gamemodel, player0tup, player1tup)
        else:
            ionest.generalStart(gamemodel, player0tup, player1tup,
                                (StringIO(ficsgame.board.fen), fen, 0, -1))

    def onObserveGameCreated (self, bm, ficsgame):
        log.debug("ICLounge.onObserveGameCreated: %s\n" % ficsgame)
        if ficsgame.board.wms == 0 and ficsgame.board.bms == 0:
            timemodel = None
        else:
            timemodel = TimeModel (ficsgame.board.wms/1000., ficsgame.inc,
                                   ficsgame.board.bms/1000.)
        gamemodel = ICGameModel (self.connection, ficsgame, timemodel)
        gamemodel.connect("game_started", lambda gamemodel:
                     self.connection.bm.onGameModelStarted(ficsgame.gameno))
        
        # The players need to start listening for moves IN this method if they
        # want to be noticed of all moves the FICS server sends us from now on
        player0 = ICPlayer(gamemodel, ficsgame.wplayer.name, ficsgame.gameno, WHITE)
        player1 = ICPlayer(gamemodel, ficsgame.bplayer.name, ficsgame.gameno, BLACK)
        
        player0tup = (REMOTE, lambda:player0, (), ficsgame.wplayer.name,
                      ficsgame.wplayer.getRatingForCurrentGame(),
                      ficsgame.wplayer.getTitles())
        player1tup = (REMOTE, lambda:player1, (), ficsgame.bplayer.name,
                      ficsgame.bplayer.getRatingForCurrentGame(),
                      ficsgame.bplayer.getTitles())
        
        ionest.generalStart(gamemodel, player0tup, player1tup,
                            (StringIO(ficsgame.board.pgn), pgn, 0, -1))

# -*- coding: utf-8 -*-

from Queue import Queue
from Queue import Empty as EmptyError
from cStringIO import StringIO
from time import sleep
from math import e
import webbrowser

import gtk, pango, re
from gtk import gdk
from gtk.gdk import pixbuf_new_from_file

from pychess.System import glock, uistuff
from pychess.System.GtkWorker import EmitPublisher, Publisher
from pychess.System.prefix import addDataPrefix
from pychess.System.ping import Pinger
from pychess.widgets import ionest
from pychess.widgets import gamewidget
from pychess.Utils.const import *
from pychess.Utils.TimeModel import TimeModel
from pychess.Utils.GameModel import GameModel
from pychess.Players.ServerPlayer import ServerPlayer
from pychess.Players.Human import Human

from DisconnectManager import dm
from GameListManager import glm
from FingerManager import fm
from NewsManager import nm
from BoardManager import bm
from OfferManager import om

from IcGameModel import IcGameModel
from SpotGraph import SpotGraph
import telnet

firstRun = True
def show():
    global firstRun
    if firstRun:
        firstRun=False
        initialize()
    
    widgets["fics_lounge"].show()


def initialize():
    
    global widgets
    class Widgets:
        def __init__ (self, glades):
            self.widgets = glades
        def __getitem__(self, key):
            return self.widgets.get_widget(key)
    widgets = Widgets(gtk.glade.XML(addDataPrefix("glade/fics_lounge.glade")))
    
    sections = (
        VariousSection(),
        UserInfoSection(),
        NewsSection(),
        
        SeekTabSection(),
        ChallengeTabSection(),
        SeekGraphSection(),
        PlayerTabSection(),
        GameTabSection(),
        AdjournedTabSection(),
        
        SeekChallengeSection(),
        
        # This is not really a section. Merely a pair of BoardManager connects
        # which takes care of ionest and stuff when a new game is started or
        # observed
        CreatedBoards()
    )
    
    def onStatusChanged (client, signal):
        for section in sections:
            if signal == IC_CONNECTED:
                section.onConnect()
            else:
                section.onDisconnect()
    telnet.connectStatus (onStatusChanged)

################################################################################
# Initialize Sections                                                          #
################################################################################

class Section:
    def onConnect (self):
        pass
    
    def onDisconnect (self):
        pass

############################################################################
# Initialize Various smaller sections                                      #
############################################################################

class VariousSection(Section):
    def __init__ (self):
        def on_window_delete (window, event):
            widgets["fics_lounge"].hide()
            return True
        widgets["fics_lounge"].connect("delete-event", on_window_delete)
        
        def on_logoffButton_clicked (button):
            dm.disconnect()
            widgets["fics_lounge"].hide()
        widgets["logoffButton"].connect("clicked", on_logoffButton_clicked)
        
        glock.acquire()
        try:
            uistuff.makeYellow(widgets["cautionBox"])
            uistuff.makeYellow(widgets["cautionHeader"])
        finally:
            glock.release()
        
        def on_learn_more_clicked (button, *args):
            retur = widgets["ficsCautionDialog"].run()
            widgets["ficsCautionDialog"].hide()
        widgets["caution_learn_more"].connect("clicked", on_learn_more_clicked)

############################################################################
# Initialize User Information Section                                      #
############################################################################

class UserInfoSection(Section):
    
    def onConnect (self):
        fm.finger(telnet.curname)
        glock.acquire()
        try:
            widgets["usernameLabel"].set_markup("<b>%s</b>" % telnet.curname)
        finally:
            glock.release()
    
    def onDisconnect (self):
        widgets["fingerTableDock"].remove(self.dock.get_children()[0])
    
    def __init__ (self):
        self.dock = widgets["fingerTableDock"]
        fm.connect("fingeringFinished", self.onFinger)
    
    def onFinger (self, fm, ratings, email, time):
        glock.acquire()
        try:
            rows = 1
            if ratings: rows += len(ratings)+1
            if email: rows += 1
            if time: rows += 1
            
            table = gtk.Table(6, rows)
            table.props.column_spacing = 12
            table.props.row_spacing = 4
            
            def label(str, xalign=0):
                label = gtk.Label(str)
                label.props.xalign = xalign
                return label
            
            row = 0
            
            if ratings:
                for i, item in enumerate((_("Rating"), _("Win"), _("Loss"), _("Draw"), _("Total"))):
                    table.attach(label(item, xalign=1), i+1,i+2,0,1)
                
                row += 1
                
                for typ, numbers in ratings.iteritems():
                    table.attach(label(_(typ)+":"), 0, 1, row, row+1)
                    # Remove RD tag, as we want to be compact
                    numbers = numbers[:1] + numbers[2:]
                    for i, number in enumerate(numbers):
                        table.attach(label(_(number), xalign=1), i+1, i+2, row, row+1)
                    row += 1
                
                table.attach(gtk.HSeparator(), 0, 6, row, row+1, ypadding=2)
                row += 1
            
            if email:
                table.attach(label(_("Email")+":"), 0, 1, row, row+1)
                table.attach(label(email), 1, 6, row, row+1)
                row += 1
            
            if time and telnet.registered:
                table.attach(label(_("Spent")+":"), 0, 1, row, row+1)
                s = ""
                if time[0]:
                    if time[0] == "1":
                        s += "%s day" % time[0]
                    else: s += "%s days" % time[0]
                if time[1]:
                    if s: s += ", "
                    if time[1] == "1":
                        s += "%s hour" % time[1]
                    else: s += "%s hrs" % time[1]
                if time[2]:
                    if s: s += ", "
                    if time[2] == "1":
                        s += "%s min" % time[2]
                    else: s += "%s mins" % time[2]
                if time[3]:
                    if s: s += ", "
                    if time[3] == "1":
                        s += "%s sec" % time[3]
                    else: s += "%s secs" % time[3]
                s += " "+_("online in total")
                table.attach(label(s), 1, 6, row, row+1)
                row += 1
            
            table.attach(label(_("Ping")+":"), 0, 1, row, row+1)
            pingLabel = gtk.Label(_("Connecting")+"...")
            pingLabel.props.xalign = 0
            pinger = Pinger("freechess.org")
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
            
            if not telnet.registered:
                vbox = gtk.VBox()
                table.attach(vbox, 0, 6, row, row+1)
                label0 = gtk.Label(_("You are currently logged in as a guest.\nA guest is not able to play rated games, and thus the offer of games is be smaller."))
                label0.props.xalign = 0
                label0.props.wrap = True
                vbox.add(label0)
                eventbox = uistuff.initLabelLinks(_("Register now"),
                        "http://freechess.org/Register/index.html")
                vbox.add(eventbox)
            
            self.dock.add(table)
            self.dock.show_all()
        finally:
            glock.release()

############################################################################
# Initialize News Section                                                  #
############################################################################

class NewsSection(Section):
    
    def onDisconnect (self):
        for child in widgets["newsVBox"].get_children():
            widgets["newsVBox"].remove(child)
    
    def __init__(self):
        nm.connect("readNews", self.onNewsItem)
    
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
            gtk.Tooltips().set_tip(expander, title)
            
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
            widgets["newsVBox"].pack_end(expander)
        finally:
            glock.release()
    
############################################################################
# Initialize Lists                                                         #
############################################################################

class ParrentListSection (Section):
    
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
    
    def pixCompareFunction (self, treemodel, iter0, iter1):
        pix0 = treemodel.get_value(iter0, 0)
        pix1 = treemodel.get_value(iter1, 0)
        if type(pix0) == gtk.gdk.Pixbuf and type(pix1) == gtk.gdk.Pixbuf:
            return cmp(pix0.get_pixels(), pix1.get_pixels())
        return cmp(pix0, pix1)

########################################################################
# Initialize Seek List                                                 #
########################################################################

class SeekTabSection (ParrentListSection):
    
    def onDisconnect (self):
        glock.acquire()
        try:
            self.store.clear()
            widgets["activeSeeksLabel"].set_text("0 %s" % _("Active Seeks"))
        finally:
            glock.release()
    
    def onConnect (self):
        self.seeks = {}
    
    def __init__ (self):
        ParrentListSection.__init__(self)
        
        self.seekPix = pixbuf_new_from_file(addDataPrefix("glade/seek.png"))
        
        glock.acquire()
        try:
            self.tv = widgets["seektreeview"]
            self.store = gtk.ListStore(str, gtk.gdk.Pixbuf, str, int, str, str, str)
            self.tv.set_model(gtk.TreeModelSort(self.store))
            self.addColumns (
                    self.tv, "GameNo", "", _("Name"), _("Rating"), _("Rated"),
                    _("Type"), _("Clock"), hide=[0], pix=[1] )
            self.tv.set_search_column(2)
            try:
                self.tv.set_search_position_func(self.lowLeftSearchPosFunc)
            except AttributeError:
                # Unknow signal name is raised by gtk < 2.10
                pass
        finally:
            glock.release()
        
        glm.connect("addSeek", lambda glm, seek:
                self.listPublisher.put((self.onAddSeek, seek)) )
        
        glm.connect("removeSeek", lambda glm, gameno:
                self.listPublisher.put((self.onRemoveSeek, gameno)) )
        
        glm.connect("clearSeeks", lambda glm:
                self.listPublisher.put((self.onClearSeeks,)) )
        
        widgets["acceptButton"].connect("clicked", self.onAccept)
        self.tv.connect("row-activated", self.onAccept)
        
        bm.connect("playBoardCreated", lambda bm, board:
                self.listPublisher.put((self.onPlayingGame,)) )
        
        bm.connect("curGameEnded", lambda bm, gameno, status, reason:
                self.listPublisher.put((self.onCurGameEnded,)) )
    
    def onAddSeek (self, seek):
        time = "%s min + %s sec" % (seek["t"], seek["i"])
        rated = seek["r"] == "u" and _("Unrated") or _("Rated")
        ti = self.store.append ([seek["gameno"], self.seekPix, seek["w"],
                                int(seek["rt"]), rated, seek["tp"], time])
        self.seeks [seek["gameno"]] = ti
        count = int(widgets["activeSeeksLabel"].get_text().split()[0])+1
        postfix = count == 1 and _("Active Seek") or _("Active Seeks")
        widgets["activeSeeksLabel"].set_text("%d %s" % (count, postfix))
        
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
        count = int(widgets["activeSeeksLabel"].get_text().split()[0])-1
        postfix = count == 1 and _("Active Seek") or _("Active Seeks")
        widgets["activeSeeksLabel"].set_text("%d %s" % (count, postfix))
        
    def onClearSeeks (self):
        self.store.clear()
        self.seeks = {}
        widgets["activeSeeksLabel"].set_text("0 %s" % _("Active Seeks"))
        
    def onAccept (self, widget, *args):
        model, iter = widgets["seektreeview"].get_selection().get_selected()
        if iter == None: return
        gameno = model.get_value(iter, 0)
        if gameno.startswith("C"):
            om.acceptIndex(gameno[1:])
        else:
            om.playIndex(gameno)
    
    def onPlayingGame (self):
        widgets["seekListContent"].set_sensitive(False)
        widgets["challengePanel"].set_sensitive(False)
        self.store.clear()
    
    def onCurGameEnded (self):
        widgets["seekListContent"].set_sensitive(True)
        widgets["challengePanel"].set_sensitive(True)
        glm.refreshSeeks()

########################################################################
# Initialize Challenge List                                            #
########################################################################

class ChallengeTabSection (ParrentListSection):
    
    def onConnect (self):
        self.challenges = {}
    
    def __init__ (self):
        ParrentListSection.__init__(self)
        self.store = widgets["seektreeview"].get_model().get_model()
        self.chaPix = pixbuf_new_from_file(addDataPrefix("glade/challenge.png"))
        
        om.connect("onChallengeAdd", lambda om, index, match:
                self.listPublisher.put((self.onChallengeAdd, index, match)) )
        
        om.connect("onChallengeRemove", lambda om, index:
                self.listPublisher.put((self.onChallengeRemove, index)) )
    
    def onChallengeAdd (self, index, match):
        time = "%s min + %s sec" % (match["t"], match["i"])
        rated = match["r"] == "u" and _("Unrated") or _("Rated")
        ti = self.store.append (["C"+index, self.chaPix, match["w"],
                                int(match["rt"]), rated, match["tp"], time])
        self.challenges [index] = ti
        count = int(widgets["activeSeeksLabel"].get_text().split()[0])+1
        postfix = count == 1 and _("Active Seek") or _("Active Seeks")
        widgets["activeSeeksLabel"].set_text("%d %s" % (count, postfix))
    
    def onChallengeRemove (self, index):
        if not index in self.challenges: return
        ti = self.challenges [index]
        if not self.store.iter_is_valid(ti): return
        self.store.remove (ti)
        del self.challenges [index]
        count = int(widgets["activeSeeksLabel"].get_text().split()[0])-1
        postfix = count == 1 and _("Active Seek") or _("Active Seeks")
        widgets["activeSeeksLabel"].set_text("%d %s" % (count, postfix))

########################################################################
# Initialize Seek Graph                                                #
########################################################################

YMARKS = (600, 1200, 1800, 2400)
YLOCATION = lambda y: y/3000.
XMARKS = (3, 6, 12, 24)
XLOCATION = lambda x: e**(-5./x)

# This is used to convert increment time to minutes. With a GAME_LENGTH on
# 40, a game on two minutes and twelve secconds will be placed at the same
# X location as a game on 2+12*40/60 = 10 minutes
GAME_LENGTH = 40

class SeekGraphSection (ParrentListSection):
    
    def onDisconnect (self):
        glock.acquire()
        try:
            self.graph.clearSpots()
        finally:
            glock.release()
    
    def __init__ (self):
        ParrentListSection.__init__(self)
        
        glock.acquire()
        try:
            self.graph = SpotGraph()
            
            for rating in YMARKS:
                self.graph.addYMark(YLOCATION(rating), str(rating))
            for mins in XMARKS:
                self.graph.addXMark(XLOCATION(mins), str(mins)+" min")
            
            widgets["graphDock"].add(self.graph)
            self.graph.show()
        finally:
            glock.release()
        
        self.graph.connect("spotClicked", self.onSpotClicked)
        
        glm.connect("addSeek", lambda glm, seek:
                self.listPublisher.put((self.onSeekAdd, seek)) )
        
        glm.connect("removeSeek", lambda glm, gameno:
                self.listPublisher.put((self.onSeekRemove, gameno)) )
        
        glm.connect("clearSeeks", lambda glm:
                self.listPublisher.put((self.onSeekClear,)) )
        
        bm.connect("playBoardCreated", lambda bm, board:
                self.listPublisher.put((self.onPlayingGame,)) )
        
        bm.connect("curGameEnded", lambda bm, gameno, status, reason:
                self.listPublisher.put((self.onCurGameEnded,)) )
        
    def onSpotClicked (self, graph, name):
        bm.play(name)
    
    def onSeekAdd (self, seek):
        x = XLOCATION (float(seek["t"]) + float(seek["i"]) * GAME_LENGTH/60.)
        y = seek["rt"].isdigit() and YLOCATION(float(seek["rt"])) or 0
        type = seek["r"] == "u" and 1 or 0
        
        text = "%s (%s)" % (seek["w"], seek["rt"])
        rated = seek["r"] == "u" and _("Unrated") or _("Rated")
        text += "\n%s %s" % (rated, seek["tp"])
        text += "\n%s min + %s sec" % (seek["t"], seek["i"])
        
        self.graph.addSpot(seek["gameno"], text, x, y, type)
        
    def onSeekRemove (self, gameno):
        self.graph.removeSpot(gameno)
        
    def onSeekClear (self):
        self.graph.clearSpots()
        
    def onPlayingGame (self):
        widgets["seekGraphContent"].set_sensitive(False)
        self.graph.clearSpots()
        
    def onCurGameEnded (self):
        widgets["seekGraphContent"].set_sensitive(True)

########################################################################
# Initialize Players List                                              #
########################################################################

class PlayerTabSection (ParrentListSection):
    
    icons = gtk.icon_theme_get_default()
    l = gtk.ICON_LOOKUP_USE_BUILTIN
    peoplepix = icons.load_icon("stock_people", 15, l)
    bookpix = icons.load_icon("stock_book_blue", 15, l)
    easypix = icons.load_icon("stock_weather-few-clouds", 15, l)
    advpix = icons.load_icon("stock_weather-cloudy", 15, l)
    exppix = icons.load_icon("stock_weather-storm", 15, l)
    cmppix = icons.load_icon("stock_notebook", 15, l)
    
    def onDisconnect (self):
        glock.acquire()
        try:
            self.store.clear()
            widgets["playersOnlineLabel"].set_text("0 %s" % _("Players Ready"))
        finally:
            glock.release()
    
    def onConnect (self):
        self.players = {}
    
    def __init__ (self):
        ParrentListSection.__init__(self)
        
        glock.acquire()
        try:
            self.tv = widgets["playertreeview"]
            self.store = gtk.ListStore(gtk.gdk.Pixbuf, str, int)
            self.tv.set_model(gtk.TreeModelSort(self.store))
            self.addColumns(self.tv, "", _("Name"), _("Rating"), pix=[0])
            self.tv.get_column(0).set_sort_column_id(0)
            self.tv.get_model().set_sort_func(0, self.pixCompareFunction)
            try:
                self.tv.set_search_position_func(self.lowLeftSearchPosFunc)
            except AttributeError:
                # Unknow signal name is raised by gtk < 2.10
                pass
        finally:
            glock.release()
        
        glm.connect("addPlayer", lambda glm, player:
                self.listPublisher.put((self.onPlayerAdd, player)) )
        
        glm.connect("removePlayer", lambda glm, name:
                self.listPublisher.put((self.onPlayerRemove, name)) )
    
    def onPlayerAdd (self, player):
        if player["name"] in self.players: return
        rating = player["rating"].isdigit() and int(player["rating"]) or 0
        title = player["title"]
        if title == "C" or title == "TD":
            title = PlayerTabSection.cmppix
        elif title == "U":
            title = PlayerTabSection.peoplepix
        elif title == None:
            if rating < 1300:
                title = PlayerTabSection.easypix
            elif rating < 1600:
                title = PlayerTabSection.advpix
            else:
                title = PlayerTabSection.exppix
        else:
            # Admins gets a book picture
            title = PlayerTabSection.bookpix
        ti = self.store.append ([title, player["name"], rating])
        self.players [player["name"]] = ti
        count = int(widgets["playersOnlineLabel"].get_text().split()[0])+1
        postfix = count == 1 and _("Player Ready") or _("Players Ready")
        widgets["playersOnlineLabel"].set_text("%d %s" % (count, postfix))
        
    def onPlayerRemove (self, name):
        if not name in self.players:
            return
        ti = self.players [name]
        if not self.store.iter_is_valid(ti):
            return
        self.store.remove (ti)
        del self.players[name]
        count = int(widgets["playersOnlineLabel"].get_text().split()[0])-1
        postfix = count == 1 and _("Player Ready") or _("Players Ready")
        widgets["playersOnlineLabel"].set_text("%d %s" % (count, postfix))

########################################################################
# Initialize Games List                                                #
########################################################################

class GameTabSection (ParrentListSection):
    
    def onDisconnect (self):
        glock.acquire()
        try:
            self.store.clear()
            widgets["gamesRunningLabel"].set_text("0 %s" % _("Games Running"))
        finally:
            glock.release()
    
    def onConnect (self):
        self.games = {}
    
    def __init__ (self):
        ParrentListSection.__init__(self)
        
        icons = gtk.icon_theme_get_default()
        self.recpix = icons.load_icon("media-record", 16, gtk.ICON_LOOKUP_USE_BUILTIN)
        self.clearpix = pixbuf_new_from_file(addDataPrefix("glade/board.png"))
        
        glock.acquire()
        try:
            self.tv = widgets["gametreeview"]
            self.store = gtk.ListStore(str, gtk.gdk.Pixbuf, str, str, str)
            self.tv.set_model(gtk.TreeModelSort(self.store))
            self.tv.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
            self.addColumns (
                    self.tv, "GameNo", "", _("White Player"), _("Black Player"),
                    _("Game Type"), hide=[0], pix=[1] )
            self.tv.get_column(0).set_sort_column_id(0)
            self.tv.get_model().set_sort_func(0, self.pixCompareFunction)
            try:
                self.tv.set_search_position_func(self.lowLeftSearchPosFunc)
            except AttributeError:
                # Unknow signal name is raised by gtk < 2.10
                pass
            def searchCallback (model, column, key, iter):
                if model.get_value(iter, 2).lower().startswith(key) or \
                   model.get_value(iter, 3).lower().startswith(key):
                    return False
                return True
            self.tv.set_search_equal_func (searchCallback)
        finally:
            glock.release()
        
        glm.connect("addGame", lambda glm, game:
                self.listPublisher.put((self.onGameAdd, game)) )
        
        glm.connect("removeGame", lambda glm, gameno:
                self.listPublisher.put((self.onGameRemove, gameno)) )
        
        widgets["observeButton"].connect ("clicked", self.onObserveClicked)
        self.tv.connect("row-activated", self.onObserveClicked)
        
        bm.connect("observeBoardCreated", lambda bm, gameno, *args:
                self.listPublisher.put((self.onGameObserved, gameno)) )
        
        bm.connect("obsGameUnobserved", lambda bm, gameno:
                self.listPublisher.put((self.onGameUnobserved, gameno)) )
    
    def onGameAdd (self, game):
        ti = self.store.append ([game["gameno"], self.clearpix, game["wn"],
                                game["bn"], game["type"]])
        self.games[game["gameno"]] = ti
        count = int(widgets["gamesRunningLabel"].get_text().split()[0])+1
        postfix = count == 1 and _("Game Running") or _("Games Running")
        widgets["gamesRunningLabel"].set_text("%d %s" % (count, postfix))
    
    def onGameRemove (self, gameno):
        if not gameno in self.games:
            return
        ti = self.games[gameno]
        if not self.store.iter_is_valid(ti):
            return
        self.store.remove (ti)
        del self.games[gameno]
        count = int(widgets["gamesRunningLabel"].get_text().split()[0])-1
        postfix = count == 1 and _("Game Running") or _("Games Running")
        widgets["gamesRunningLabel"].set_text("%d %s" % (count, postfix))
    
    def onObserveClicked (self, widget, *args):
        model, paths = self.tv.get_selection().get_selected_rows()
        for path in paths:
            rowiter = model.get_iter(path)
            gameno = model.get_value(rowiter, 0)
            bm.observe(gameno)
    
    def onGameObserved (self, gameno):
        threeiter = self.games[gameno]
        self.store.set_value (threeiter, 1, self.recpix)
    
    def onGameUnobserved (self, gameno):
        threeiter = self.games[gameno]
        self.store.set_value(threeiter, 1, self.clearpix)

########################################################################
# Initialize Adjourned List                                            #
########################################################################
# We skip adjourned games until Staunton

class AdjournedTabSection (ParrentListSection):
    
    def __init__ (self):
        ParrentListSection.__init__(self)
        
        widgets["notebook"].remove_page(4)
        
        #if not telnet.registered:
        #    widgets["notebook"].remove_page(4)
        #else:
        #    tv = widgets["adjournedtreeview"]
        #    astore = gtk.ListStore (str, str, str, str)
        #    tv.set_model (gtk.TreeModelSort (astore))
        #    addColumns (tv, _("Opponent"), _("Status"), _("% Played"), _("Date"))
        #    
        #    def on_adjourn_add (glm, game):
        #        def call ():
        #            ti = astore.append ([game["opponent"], game["opstatus"],
        #                             "%d %%" % game["procPlayed"], game["date"]])
        #        listPublisher.put(call)
        #    glm.connect("addAdjourn", on_adjourn_add)
    
############################################################################
# Initialize seeking-/challengingpanel                                     #
############################################################################

class SeekChallengeSection (ParrentListSection):
    
    def onConnect (self):
        glock.acquire()
        try:
            if not telnet.registered:
                widgets["ratedGameCheck"].hide()
                widgets["chaRatedGameCheck"].hide()
            else:
                widgets["ratedGameCheck"].show()
                widgets["chaRatedGameCheck"].show()
        finally:
            glock.release()
    
    def __init__ (self):
        ParrentListSection.__init__(self)
        
        glock.acquire()
        try:
            liststore = gtk.ListStore(str, str)
            liststore.append(["0 → 1300", _("Easy")])
            liststore.append(["1300 → 1600", _("Advanced")])
            liststore.append(["1600 → 9999", _("Expert")])
            widgets["strengthCombobox"].set_model(liststore)
            cell = gtk.CellRendererText()
            cell.set_property('xalign',1)
            widgets["strengthCombobox"].pack_start(cell)
            widgets["strengthCombobox"].add_attribute(cell, 'text', 1)
            widgets["strengthCombobox"].set_active(0)
            
            liststore = gtk.ListStore(str)
            liststore.append([_("Don't Care")])
            liststore.append([_("Want White")])
            liststore.append([_("Want Black")])
            widgets["colorCombobox"].set_model(liststore)
            widgets["colorCombobox"].set_active(0)
            widgets["chaColorCombobox"].set_model(liststore)
            widgets["chaColorCombobox"].set_active(0)
            
            liststore = gtk.ListStore(str, str)
            chaliststore = gtk.ListStore(str, str)
            for store in (liststore, chaliststore):
                store.append(["15 min + 10", _("Normal")])
                store.append(["5 min + 2", _("Blitz")])
                store.append(["1 min + 0", _("Lightning")])
                store.append(["", _("New Custom")])
            cell = gtk.CellRendererText()
            cell.set_property('xalign',1)
            widgets["timeCombobox"].set_model(liststore)
            widgets["timeCombobox"].pack_start(cell)
            widgets["timeCombobox"].add_attribute(cell, 'text', 1)
            widgets["timeCombobox"].set_active(0)
            widgets["chaTimeCombobox"].set_model(chaliststore)
            widgets["chaTimeCombobox"].pack_start(cell)
            widgets["chaTimeCombobox"].add_attribute(cell, 'text', 1)
            widgets["chaTimeCombobox"].set_active(0)
            
            widgets["timeCombobox"].old_active = 0
            widgets["chaTimeCombobox"].old_active = 0
        finally:
            glock.release()
        
        widgets["timeCombobox"].connect(
                "changed", self.onTimeComboboxChanged, widgets["chaTimeCombobox"])
        widgets["chaTimeCombobox"].connect(
                "changed", self.onTimeComboboxChanged, widgets["timeCombobox"])
        
        widgets["seekButton"].connect("clicked", self.onSeekButtonClicked)
        widgets["challengeButton"].connect("clicked", self.onChallengeButtonClicked)
        
        seekSelection = widgets["seektreeview"].get_selection()
        seekSelection.connect_after("changed", self.onSeekSelectionChanged)
        
        playerSelection = widgets["playertreeview"].get_selection()
        playerSelection.connect_after("changed", self.onPlayerSelectionChanged)
    
    def onTimeComboboxChanged (self, combo, othercombo):
        if combo.get_active() == 3:
            response = widgets["customTimeDialog"].run()
            widgets["customTimeDialog"].hide()
            if response != gtk.RESPONSE_OK:
                combo.set_active(combo.old_active)
                return
            if len(combo.get_model()) == 5:
                del combo.get_model()[4]
            minutes = widgets["minSpinbutton"].get_value()
            gain = widgets["gainSpinbutton"].get_value()
            text = "%d min + %d" % (minutes, gain)
            combo.get_model().append([text, _("Custom")])
            combo.set_active(4)
        else:
            combo.old_active = combo.get_active()
    
    def onSeekButtonClicked (self, button):
        ratingrange = map(int, widgets["strengthCombobox"].get_model()[
                widgets["strengthCombobox"].get_active()][0].split(" → "))
        rated = widgets["ratedGameCheck"].get_active()
        color = widgets["colorCombobox"].get_active()-1
        if color == -1: color = None
        min, incr = map(int, widgets["timeCombobox"].get_model()[
                widgets["timeCombobox"].get_active()][0].split(" min +"))
        glm.seek(min, incr, rated, ratingrange, color)
    
    def onChallengeButtonClicked (self, button):
        model, iter = widgets["playertreeview"].get_selection().get_selected()
        if iter == None: return
        playerName = model.get_value(iter, 1)
        rated = widgets["chaRatedGameCheck"].get_active()
        color = widgets["chaColorCombobox"].get_active()-1
        if color == -1: color = None
        min, incr = map(int, widgets["chaTimeCombobox"].get_model()[
                widgets["chaTimeCombobox"].get_active()][0].split(" min +"))
        glm.challenge(playerName, min, incr, rated, color)
    
    def onSeekSelectionChanged (self, selection):
        # You can't press challengebutton when nobody are selected
        isAnythingSelected = selection.get_selected()[1] != None
        widgets["acceptButton"].set_sensitive(isAnyThingSelected)
    
    def onPlayerSelectionChanged (self, selection):
        model, iter = selection.get_selected()
        
        # You can't press challengebutton when nobody are selected
        isAnythingSelected = iter != None
        widgets["challengeButton"].set_sensitive(isAnythingSelected)
        
        if isAnythingSelected:
            # You can't challenge a guest to a rated game
            playerTitle = model.get_value(iter, 0)
            isGuestPlayer = playerTitle == PlayerTabSection.peoplepix
        widgets["chaRatedGameCheck"].set_sensitive(
                not isAnythingSelected or not isGuestPlayer)

############################################################################
# Initialize connects for createBoard and createObsBoard                   #
############################################################################

class CreatedBoards (Section):
    
    def __init__ (self):
        bm.connect ("playBoardCreated", self.playBoardCreated)
        bm.connect ("observeBoardCreated", self.observeBoardCreated)
    
    def playBoardCreated (self, bm, board):
        timemodel = TimeModel (int(board["mins"])*60, int(board["incr"]))
        game = IcGameModel (board["gameno"], timemodel)
        gmwidg = gamewidget.GameWidget(game)
        
        if board["wname"].lower() == telnet.curname.lower():
            color = WHITE
            white = Human(gmwidg, WHITE, board["wname"])
            black = ServerPlayer (game, board["bname"], False, board["gameno"], BLACK)
        else:
            color = BLACK
            black = Human(gmwidg, BLACK, board["bname"])
            white = ServerPlayer (game, board["wname"], False, board["gameno"], WHITE)
        
        game.setPlayers((white,black))
        
        gmwidg.setTabText("%s %s %s" % (repr(white), _("vs"), repr(black)))
        gmwidg.connect("closed", ionest.closeGame, game)
        if timemodel:
            gmwidg.widgets["ccalign"].show()
            gmwidg.widgets["cclock"].setModel(timemodel)
        
        glock.acquire()
        try:
            ionest.simpleNewGame (game, gmwidg)
            gamewidget.attachGameWidget (gmwidg)
        finally:
            glock.release()
    
    def observeBoardCreated (self, bm, gameno, pgn, secs, incr, wname, bname):
        timemodel = TimeModel (secs, incr)
        game = IcGameModel (gameno, timemodel)
        white = ServerPlayer (game, wname, True, gameno, WHITE)
        black = ServerPlayer (game, bname, True, gameno, BLACK)
        game.setPlayers((white,black))
        
        gmwidg = gamewidget.GameWidget(game)
        gmwidg.setTabText("%s %s %s" % (wname, _("vs"), bname))
        gmwidg.connect("closed", ionest.closeGame, game)
        
        if timemodel:
            gmwidg.widgets["ccalign"].show()
            gmwidg.widgets["cclock"].setModel(timemodel)
        
        def onClose (handler, closedGmwidg, game):
            if closedGmwidg == gmwidg:
                bm.unobserve(gameno)
        ionest.handler.connect("game_closed", onClose)
        
        file = StringIO(pgn)
        ionest.simpleLoadGame (game, gmwidg, file, ionest.enddir["pgn"])
        
        glock.acquire()
        try:
            gamewidget.attachGameWidget(gmwidg)
        finally:
            glock.release()

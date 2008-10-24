# -*- coding: utf-8 -*-

from Queue import Queue
from Queue import Empty as EmptyError
from cStringIO import StringIO
from time import sleep, strftime, localtime
from math import e
import webbrowser

import gtk, pango, re
from gtk import gdk
from gtk.gdk import pixbuf_new_from_file

from pychess.System import glock, uistuff
from pychess.System.GtkWorker import EmitPublisher, Publisher
from pychess.System.prefix import addDataPrefix
from pychess.System.ping import Pinger
from pychess.System.Log import log
from pychess.widgets import ionest
from pychess.widgets import gamewidget
from pychess.widgets.ChatWindow import ChatWindow
from pychess.widgets.SpotGraph import SpotGraph
from pychess.Utils.const import *
from pychess.Utils.TimeModel import TimeModel
from pychess.Utils.GameModel import GameModel
from pychess.Players.ICPlayer import ICPlayer
from pychess.Players.Human import Human
from pychess.Savers import pgn

from ICGameModel import ICGameModel

class ICLounge:
    def __init__ (self, c):
        
        self.widgets = w = uistuff.GladeWidgets("fics_lounge.glade")
        uistuff.keepWindowSize("fics_lounge", self.widgets["fics_lounge"])
        
        glock.acquire()
        try:
            sections = (
                VariousSection(w,c),
                UserInfoSection(w,c),
                NewsSection(w,c),
                
                SeekTabSection(w,c),
                ChallengeTabSection(w,c),
                SeekGraphSection(w,c),
                PlayerTabSection(w,c),
                GameTabSection(w,c),
                AdjournedTabSection(w,c),
                
                ChatWindow(w,c),
                #ConsoleWindow(w,c),
                
                SeekChallengeSection(w,c),
                
                # This is not really a section. Merely a pair of BoardManager connects
                # which takes care of ionest and stuff when a new game is started or
                # observed
                CreatedBoards(w,c)
            )
        finally:
            glock.release()
    
    def show (self):
        self.widgets["fics_lounge"].show()

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
        def on_window_delete (window, event):
            widgets["fics_lounge"].hide()
            return True
        widgets["fics_lounge"].connect("delete-event", on_window_delete)
        
        def on_logoffButton_clicked (button):
            widgets["fics_lounge"].emit("delete-event", None)
            connection.disconnect()
        widgets["logoffButton"].connect("clicked", on_logoffButton_clicked)
        
        sizeGroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        sizeGroup.add_widget(widgets["show_chat_label"])
        sizeGroup.add_widget(widgets["show_console_label"])
        sizeGroup.add_widget(widgets["log_off_label"])
        
        uistuff.makeYellow(widgets["cautionBox"])
        uistuff.makeYellow(widgets["cautionHeader"])
        
        def on_learn_more_clicked (button, *args):
            retur = widgets["ficsCautionDialog"].run()
            widgets["ficsCautionDialog"].hide()
        widgets["caution_learn_more"].connect("clicked", on_learn_more_clicked)
        
        connection.em.connect("onCommandNotFound", lambda em, cmd:
                log.error("Fics answered '%s': Command not found" % cmd))

############################################################################
# Initialize User Information Section                                      #
############################################################################

class UserInfoSection(Section):
    
    def __init__ (self, widgets, connection):
        self.widgets = widgets
        self.connection = connection
        
        self.dock = self.widgets["fingerTableDock"]
        
        self.connection.fm.connect("fingeringFinished", self.onFinger)
        self.connection.fm.finger(self.connection.getUsername())
        self.connection.bm.connect("curGameEnded", lambda *args:
                self.connection.fm.finger(self.connection.getUsername()))
        
        self.widgets["usernameLabel"].set_markup(
                "<b>%s</b>" % self.connection.getUsername())
    
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
            
            def label(value, xalign=0):
                if type(value) == float:
                    value = str(int(value))
                label = gtk.Label(value)
                label.props.xalign = xalign
                return label
            
            row = 0
            
            if finger.getRating():
                for i, item in enumerate((_("Rating"), _("Win"), _("Draw"), _("Loss"))):
                    table.attach(label(item, xalign=1), i+1,i+2,0,1)
                row += 1
                
                for type_, rating in finger.getRating().iteritems():
                    table.attach(label(typeName[type_]+":"), 0, 1, row, row+1)
                    table.attach(label(rating.elo, xalign=1), 1, 2, row, row+1)
                    table.attach(label(rating.wins, xalign=1), 2, 3, row, row+1)
                    table.attach(label(rating.draws, xalign=1), 3, 4, row, row+1)
                    table.attach(label(rating.losses, xalign=1), 4, 5, row, row+1)
                    row += 1
                
                table.attach(gtk.HSeparator(), 0, 6, row, row+1, ypadding=2)
                row += 1
            
            if finger.getEmail():
                table.attach(label(_("Email")+":"), 0, 1, row, row+1)
                table.attach(label(finger.getEmail()), 1, 6, row, row+1)
                row += 1
            
            if finger.getCreated():
                table.attach(label(_("Spent")+":"), 0, 1, row, row+1)
                s = time.strftime("%Y %B %d ", time.localtime(time.time()))
                s += _("online in total")
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
            
            if not self.connection.isRegistred():
                vbox = gtk.VBox()
                table.attach(vbox, 0, 6, row, row+1)
                label0 = gtk.Label(_("You are currently logged in as a guest.\nA guest is not able to play rated games, and thus the offer of games is be smaller."))
                label0.props.xalign = 0
                label0.props.wrap = True
                label0.props.width_request = 300
                vbox.add(label0)
                eventbox = uistuff.initLabelLinks(_("Register now"),
                        "http://freechess.org/Register/index.html")
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

########################################################################
# Initialize Seek List                                                 #
########################################################################

class SeekTabSection (ParrentListSection):
    
    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)
        
        self.widgets = widgets
        self.connection = connection
        
        self.seeks = {}
        
        self.seekPix = pixbuf_new_from_file(addDataPrefix("glade/seek.png"))
        self.manSeekPix = pixbuf_new_from_file(addDataPrefix("glade/manseek.png"))
        
        self.tv = self.widgets["seektreeview"]
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
        
        self.connection.glm.connect("addSeek", lambda glm, seek:
                self.listPublisher.put((self.onAddSeek, seek)) )
        
        self.connection.glm.connect("removeSeek", lambda glm, gameno:
                self.listPublisher.put((self.onRemoveSeek, gameno)) )
        
        self.connection.glm.connect("clearSeeks", lambda glm:
                self.listPublisher.put((self.onClearSeeks,)) )
        
        self.widgets["acceptButton"].connect("clicked", self.onAccept)
        self.tv.connect("row-activated", self.onAccept)
        
        self.connection.bm.connect("playBoardCreated", lambda bm, board:
                self.listPublisher.put((self.onPlayingGame,)) )
        
        self.connection.bm.connect("curGameEnded", lambda bm, gameno, status, reason:
                self.listPublisher.put((self.onCurGameEnded,)) )
    
    def onAddSeek (self, seek):
        time = "%s min + %s sec" % (seek["t"], seek["i"])
        rated = seek["r"] == "u" and _("Unrated") or _("Rated")
        pix = seek["manual"] and self.manSeekPix or self.seekPix
        ti = self.store.append ([seek["gameno"], pix, seek["w"],
                                int(seek["rt"]), rated, seek["tp"], time])
        self.seeks [seek["gameno"]] = ti
        count = int(self.widgets["activeSeeksLabel"].get_text().split()[0])+1
        postfix = count == 1 and _("Active Seek") or _("Active Seeks")
        self.widgets["activeSeeksLabel"].set_text("%d %s" % (count, postfix))
        
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
        count = int(self.widgets["activeSeeksLabel"].get_text().split()[0])-1
        postfix = count == 1 and _("Active Seek") or _("Active Seeks")
        self.widgets["activeSeeksLabel"].set_text("%d %s" % (count, postfix))
        
    def onClearSeeks (self):
        self.store.clear()
        self.seeks = {}
        self.widgets["activeSeeksLabel"].set_text("0 %s" % _("Active Seeks"))
        
    def onAccept (self, widget, *args):
        model, iter = self.widgets["seektreeview"].get_selection().get_selected()
        if iter == None: return
        gameno = model.get_value(iter, 0)
        if gameno.startswith("C"):
            self.connection.om.acceptIndex(gameno[1:])
        else:
            self.connection.om.playIndex(gameno)
    
    def onPlayingGame (self):
        self.widgets["seekListContent"].set_sensitive(False)
        self.widgets["challengePanel"].set_sensitive(False)
        self.store.clear()
        self.widgets["activeSeeksLabel"].set_text("0 %s" % _("Active Seeks"))
    
    def onCurGameEnded (self):
        self.widgets["seekListContent"].set_sensitive(True)
        self.widgets["challengePanel"].set_sensitive(True)
        self.connection.glm.refreshSeeks()

########################################################################
# Initialize Challenge List                                            #
########################################################################

class ChallengeTabSection (ParrentListSection):
    
    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)
        
        self.widgets = widgets
        self.connection = connection
        
        self.challenges = {}
        
        self.store = self.widgets["seektreeview"].get_model().get_model()
        self.chaPix = pixbuf_new_from_file(addDataPrefix("glade/challenge.png"))
        
        self.connection.om.connect("onChallengeAdd", lambda om, index, match:
                self.listPublisher.put((self.onChallengeAdd, index, match)) )
        
        self.connection.om.connect("onChallengeRemove", lambda om, index:
                self.listPublisher.put((self.onChallengeRemove, index)) )
    
    def onChallengeAdd (self, index, match):
        time = "%s min + %s sec" % (match["t"], match["i"])
        rated = match["r"] == "u" and _("Unrated") or _("Rated")
        ti = self.store.append (["C"+index, self.chaPix, match["w"],
                                int(match["rt"]), rated, match["tp"], time])
        self.challenges [index] = ti
        count = int(self.widgets["activeSeeksLabel"].get_text().split()[0])+1
        postfix = count == 1 and _("Active Seek") or _("Active Seeks")
        self.widgets["activeSeeksLabel"].set_text("%d %s" % (count, postfix))
    
    def onChallengeRemove (self, index):
        if not index in self.challenges: return
        ti = self.challenges [index]
        if not self.store.iter_is_valid(ti): return
        self.store.remove (ti)
        del self.challenges [index]
        count = int(self.widgets["activeSeeksLabel"].get_text().split()[0])-1
        postfix = count == 1 and _("Active Seek") or _("Active Seeks")
        self.widgets["activeSeeksLabel"].set_text("%d %s" % (count, postfix))

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
            self.graph.addXMark(XLOCATION(mins), str(mins)+" min")
        
        self.widgets["graphDock"].add(self.graph)
        self.graph.show()
        
        self.graph.connect("spotClicked", self.onSpotClicked)
        
        self.connection.glm.connect("addSeek", lambda glm, seek:
                self.listPublisher.put((self.onSeekAdd, seek)) )
        
        self.connection.glm.connect("removeSeek", lambda glm, gameno:
                self.listPublisher.put((self.onSeekRemove, gameno)) )
        
        self.connection.glm.connect("clearSeeks", lambda glm:
                self.listPublisher.put((self.onSeekClear,)) )
        
        self.connection.bm.connect("playBoardCreated", lambda bm, board:
                self.listPublisher.put((self.onPlayingGame,)) )
        
        self.connection.bm.connect("curGameEnded", lambda bm, gameno, status, reason:
                self.listPublisher.put((self.onCurGameEnded,)) )
        
    def onSpotClicked (self, graph, name):
        self.connection.bm.play(name)
    
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
        self.widgets["seekGraphContent"].set_sensitive(False)
        self.graph.clearSpots()
        
    def onCurGameEnded (self):
        self.widgets["seekGraphContent"].set_sensitive(True)

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
    
    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)
        
        self.widgets = widgets
        self.connection = connection
        
        self.players = {}
        
        self.tv = self.widgets["playertreeview"]
        self.store = gtk.ListStore(gtk.gdk.Pixbuf, str, int)
        self.tv.set_model(gtk.TreeModelSort(self.store))
        self.addColumns(self.tv, "", _("Name"), _("Rating"), pix=[0])
        self.tv.get_column(0).set_sort_column_id(0)
        self.tv.get_model().set_sort_func(0, self.pixCompareFunction, 0)
        try:
            self.tv.set_search_position_func(self.lowLeftSearchPosFunc)
        except AttributeError:
            # Unknow signal name is raised by gtk < 2.10
            pass
        
        self.connection.glm.connect("addPlayer", lambda glm, player:
                self.listPublisher.put((self.onPlayerAdd, player)) )
        
        self.connection.glm.connect("removePlayer", lambda glm, name:
                self.listPublisher.put((self.onPlayerRemove, name)) )
    
    def onPlayerAdd (self, player):
        if player["name"] in self.players: return
        rating = player["rating"]
        title = player["title"]
        if title & 0x02:
            title = PlayerTabSection.cmppix
        elif not rating:
            title = PlayerTabSection.peoplepix
        else:
            if rating < 1300:
                title = PlayerTabSection.easypix
            elif rating < 1600:
                title = PlayerTabSection.advpix
            else:
                title = PlayerTabSection.exppix
        #else:
        #    # Admins gets a book picture
        #    title = PlayerTabSection.bookpix
        ti = self.store.append ([title, player["name"], rating])
        self.players [player["name"]] = ti
        count = int(self.widgets["playersOnlineLabel"].get_text().split()[0])+1
        postfix = count == 1 and _("Player Ready") or _("Players Ready")
        self.widgets["playersOnlineLabel"].set_text("%d %s" % (count, postfix))
        
    def onPlayerRemove (self, name):
        if not name in self.players:
            return
        ti = self.players [name]
        if not self.store.iter_is_valid(ti):
            return
        self.store.remove (ti)
        del self.players[name]
        count = int(self.widgets["playersOnlineLabel"].get_text().split()[0])-1
        postfix = count == 1 and _("Player Ready") or _("Players Ready")
        self.widgets["playersOnlineLabel"].set_text("%d %s" % (count, postfix))

########################################################################
# Initialize Games List                                                #
########################################################################

class GameTabSection (ParrentListSection):
    
    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)
        
        self.widgets = widgets
        self.connection = connection
        
        self.games = {}
        
        icons = gtk.icon_theme_get_default()
        self.recpix = icons.load_icon("media-record", 16, gtk.ICON_LOOKUP_USE_BUILTIN)
        self.clearpix = pixbuf_new_from_file(addDataPrefix("glade/board.png"))
        
        self.tv = self.widgets["gametreeview"]
        self.store = gtk.ListStore(str, gtk.gdk.Pixbuf, str, str, str)
        self.tv.set_model(gtk.TreeModelSort(self.store))
        self.tv.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.addColumns (
                self.tv, "GameNo", "", _("White Player"), _("Black Player"),
                _("Game Type"), hide=[0], pix=[1] )
        self.tv.get_column(0).set_sort_column_id(0)
        self.tv.get_model().set_sort_func(0, self.pixCompareFunction, 1)
        
        #TODO: This is all too ugly. Better use some cosnt values or something
        speeddic = {_("Lightning"):0, _("Blitz"):1, _("Standard"):2, None:3}
        def typeCompareFunction (treemodel, iter0, iter1):
            return cmp (speeddic[treemodel.get_value(iter0, 4)],
                        speeddic[treemodel.get_value(iter1, 4)])
        self.tv.get_model().set_sort_func(4, typeCompareFunction)
        
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
        
        self.connection.glm.connect("addGame", lambda glm, game:
                self.listPublisher.put((self.onGameAdd, game)) )
        
        self.connection.glm.connect("removeGame", lambda glm, gameno, res, com:
                self.listPublisher.put((self.onGameRemove, gameno)) )
        
        self.widgets["observeButton"].connect ("clicked", self.onObserveClicked)
        self.tv.connect("row-activated", self.onObserveClicked)
        
        self.connection.bm.connect("observeBoardCreated", lambda bm, gameno, *args:
                self.listPublisher.put((self.onGameObserved, gameno)) )
        
        self.connection.bm.connect("obsGameUnobserved", lambda bm, gameno:
                self.listPublisher.put((self.onGameUnobserved, gameno)) )
    
    def onGameAdd (self, game):
        ti = self.store.append ([game["gameno"], self.clearpix, game["wn"],
                                game["bn"], game["type"]])
        self.games[game["gameno"]] = ti
        count = int(self.widgets["gamesRunningLabel"].get_text().split()[0])+1
        postfix = count == 1 and _("Game Running") or _("Games Running")
        self.widgets["gamesRunningLabel"].set_text("%d %s" % (count, postfix))
    
    def onGameRemove (self, gameno):
        if not gameno in self.games:
            return
        ti = self.games[gameno]
        if not self.store.iter_is_valid(ti):
            return
        self.store.remove (ti)
        del self.games[gameno]
        count = int(self.widgets["gamesRunningLabel"].get_text().split()[0])-1
        postfix = count == 1 and _("Game Running") or _("Games Running")
        self.widgets["gamesRunningLabel"].set_text("%d %s" % (count, postfix))
    
    def onObserveClicked (self, widget, *args):
        model, paths = self.tv.get_selection().get_selected_rows()
        for path in paths:
            rowiter = model.get_iter(path)
            gameno = model.get_value(rowiter, 0)
            self.connection.bm.observe(gameno)
    
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
    
    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)
        
        widgets["notebook"].remove_page(4)
        
        #if not connection.registered:
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
    
    def __init__ (self, widgets, connection):
        ParrentListSection.__init__(self)
        
        self.widgets = widgets
        self.connection = connection
        
        liststore = gtk.ListStore(str, str)
        liststore.append([_("Don't Care"), ""])
        liststore.append(["0 → 1300", _("Easy")])
        liststore.append(["1300 → 1600", _("Advanced")])
        liststore.append(["1600 → 9999", _("Expert")])
        self.widgets["strengthCombobox"].set_model(liststore)
        cell = gtk.CellRendererText()
        cell.set_property('xalign',1)
        self.widgets["strengthCombobox"].pack_start(cell)
        self.widgets["strengthCombobox"].add_attribute(cell, 'text', 1)
        self.widgets["strengthCombobox"].set_active(0)
        
        liststore = gtk.ListStore(str)
        liststore.append([_("Don't Care")])
        liststore.append([_("Want White")])
        liststore.append([_("Want Black")])
        self.widgets["colorCombobox"].set_model(liststore)
        self.widgets["colorCombobox"].set_active(0)
        self.widgets["chaColorCombobox"].set_model(liststore)
        self.widgets["chaColorCombobox"].set_active(0)
        
        liststore = gtk.ListStore(str, str)
        chaliststore = gtk.ListStore(str, str)
        for store in (liststore, chaliststore):
            store.append(["15 min + 10", _("Normal")])
            store.append(["5 min + 2", _("Blitz")])
            store.append(["1 min + 0", _("Lightning")])
            store.append(["", _("New Custom")])
        cell = gtk.CellRendererText()
        cell.set_property('xalign',1)
        self.widgets["timeCombobox"].set_model(liststore)
        self.widgets["timeCombobox"].pack_start(cell)
        self.widgets["timeCombobox"].add_attribute(cell, 'text', 1)
        self.widgets["timeCombobox"].set_active(0)
        self.widgets["chaTimeCombobox"].set_model(chaliststore)
        self.widgets["chaTimeCombobox"].pack_start(cell)
        self.widgets["chaTimeCombobox"].add_attribute(cell, 'text', 1)
        self.widgets["chaTimeCombobox"].set_active(0)
        
        self.widgets["timeCombobox"].old_active = 0
        self.widgets["chaTimeCombobox"].old_active = 0
    
        if not connection.isRegistred():
            self.widgets["ratedGameCheck"].hide()
            self.widgets["chaRatedGameCheck"].hide()
        else:
            self.widgets["ratedGameCheck"].show()
            self.widgets["chaRatedGameCheck"].show()
        
        self.widgets["timeCombobox"].connect(
                "changed", self.onTimeComboboxChanged, self.widgets["chaTimeCombobox"])
        self.widgets["chaTimeCombobox"].connect(
                "changed", self.onTimeComboboxChanged, self.widgets["timeCombobox"])
        
        self.widgets["seekButton"].connect("clicked", self.onSeekButtonClicked)
        self.widgets["challengeButton"].connect("clicked", self.onChallengeButtonClicked)
        
        seekSelection = self.widgets["seektreeview"].get_selection()
        seekSelection.connect_after("changed", self.onSeekSelectionChanged)
        
        playerSelection = self.widgets["playertreeview"].get_selection()
        playerSelection.connect_after("changed", self.onPlayerSelectionChanged)
    
    def onTimeComboboxChanged (self, combo, othercombo):
        if combo.get_active() == 3:
            response = self.widgets["customTimeDialog"].run()
            self.widgets["customTimeDialog"].hide()
            if response != gtk.RESPONSE_OK:
                combo.set_active(combo.old_active)
                return
            if len(combo.get_model()) == 5:
                del combo.get_model()[4]
            minutes = self.widgets["minSpinbutton"].get_value()
            gain = self.widgets["gainSpinbutton"].get_value()
            text = "%d min + %d" % (minutes, gain)
            combo.get_model().append([text, _("Custom")])
            combo.set_active(4)
        else:
            combo.old_active = combo.get_active()
    
    def onSeekButtonClicked (self, button):
        item = self.widgets["strengthCombobox"].get_model()[
                   self.widgets["strengthCombobox"].get_active()]
        if item[0] == _("Don't Care"):
            ratingrange = (0, 9999)
        else: ratingrange = map(int, item[1].split(" → "))
        rated = self.widgets["ratedGameCheck"].get_active()
        color = self.widgets["colorCombobox"].get_active()-1
        if color == -1: color = None
        min, incr = map(int, self.widgets["timeCombobox"].get_model()[
                self.widgets["timeCombobox"].get_active()][0].split(" min +"))
        self.connection.glm.seek(min, incr, rated, ratingrange, color)
    
    def onChallengeButtonClicked (self, button):
        model, iter = self.widgets["playertreeview"].get_selection().get_selected()
        if iter == None: return
        playerName = model.get_value(iter, 1)
        rated = self.widgets["chaRatedGameCheck"].get_active()
        color = self.widgets["chaColorCombobox"].get_active()-1
        if color == -1: color = None
        min, incr = map(int, self.widgets["chaTimeCombobox"].get_model()[
                self.widgets["chaTimeCombobox"].get_active()][0].split(" min +"))
        self.connection.glm.challenge(playerName, min, incr, rated, color)
    
    def onSeekSelectionChanged (self, selection):
        # You can't press challengebutton when nobody are selected
        isAnythingSelected = selection.get_selected()[1] != None
        self.widgets["acceptButton"].set_sensitive(isAnythingSelected)
    
    def onPlayerSelectionChanged (self, selection):
        model, iter = selection.get_selected()
        
        # You can't press challengebutton when nobody are selected
        isAnythingSelected = iter != None
        self.widgets["challengeButton"].set_sensitive(isAnythingSelected)
        
        if isAnythingSelected:
            # You can't challenge a guest to a rated game
            playerTitle = model.get_value(iter, 0)
            isGuestPlayer = playerTitle == PlayerTabSection.peoplepix
        self.widgets["chaRatedGameCheck"].set_sensitive(
                not isAnythingSelected or not isGuestPlayer)

class ConsoleWindow:
    def __init__ (self, widgets, connection):
        pass

############################################################################
# Initialize connects for createBoard and createObsBoard                   #
############################################################################

class CreatedBoards (Section):
    
    def __init__ (self, widgets, connection):
        self.connection = connection
        self.connection.bm.connect ("playBoardCreated", self.playBoardCreated)
        self.connection.bm.connect ("observeBoardCreated", self.observeBoardCreated)
    
    def playBoardCreated (self, bm, board):
        timemodel = TimeModel (int(board["mins"])*60, int(board["incr"]))
        game = ICGameModel (self.connection, board["gameno"], timemodel)
        
        if board["wname"].lower() == self.connection.getUsername().lower():
            player0tup = (LOCAL, Human, (WHITE, ""), _("Human"))
            player1tup = (REMOTE, ICPlayer,
                    (game, board["bname"], board["gameno"], BLACK), board["bname"])
        else:
            player1tup = (LOCAL, Human, (BLACK, ""), _("Human"))
            # If the remote player is WHITE, we need to init him right now, so
            # we can catch fast made moves
            player0 = ICPlayer(game, board["wname"], board["gameno"], WHITE)
            player0tup = (REMOTE, lambda:player0, (), board["wname"])
        
        ionest.generalStart(game, player0tup, player1tup)
    
    def observeBoardCreated (self, bm, gameno, pgndata, secs, incr, wname, bname):
        timemodel = TimeModel (secs, incr)
        game = ICGameModel (self.connection, gameno, timemodel)
        
        # The players need to start listening for moves IN this method if they
        # want to be noticed of all moves the FICS server sends us from now on
        player0 = ICPlayer(game, wname, gameno, WHITE)
        player1 = ICPlayer(game, bname, gameno, BLACK)
        
        player0tup = (REMOTE, lambda:player0, (), wname)
        player1tup = (REMOTE, lambda:player1, (), bname)
        
        ionest.generalStart(
                game, player0tup, player1tup, (StringIO(pgndata), pgn, 0, -1))

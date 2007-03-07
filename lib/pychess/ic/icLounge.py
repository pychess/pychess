import gtk
from Queue import Queue
from Queue import Empty as EmptyError
from time import sleep
import telnet
from gobject import idle_add
from pychess.Utils.const import *
from GameListManager import GameListManager
from SpotGraph import SpotGraph
from math import e

firstRun = True
def show():
    global firstRun
    if firstRun:
        firstRun=False
        initialize()
    
    widgets["fics_lounge"].show()
    glm.start()
    
def initialize():
    
    global widgets
    class Widgets:
        def __init__ (self, glades):
            self.widgets = glades
        def __getitem__(self, key):
            return self.widgets.get_widget(key)
    widgets = Widgets(gtk.glade.XML(prefix("glade/fics_lounge.glade")))
    
    global glm
    glm = GameListManager()
    
    def on_status_changed (client, signal):
        if signal == IC_CONNECTED:
            glm.start ()
    telnet.connectStatus (on_status_changed)
    
    def on_window_delete (window, event):
        telnet.client.close()
    widgets["fics_lounge"].connect("delete-event", on_window_delete)
    
    def on_showConsoleButton_clicked (button):
        widgets["consoleVbox"].show()
        widgets["showConsoleButton"].hide()
    widgets["showConsoleButton"].connect(
            "clicked", on_showConsoleButton_clicked)
    
    def on_consoleCloseButton_clicked (button):
        width, height = widgets["fics_lounge"].get_size()
        widgets["consoleVbox"].hide()
        widgets["showConsoleButton"].show()
        widgets["fics_lounge"].resize(1, height)
    widgets["consoleCloseButton"].connect(
            "clicked", on_consoleCloseButton_clicked)
    
    ############################################################################
    # Initialize Lists                                                         #
    ############################################################################
    
    listqueue = Queue()
    
    def executeQueue ():
        try:
            func = listqueue.get(block=False)
            func()
        except EmptyError:
            sleep(0.01) # Make sure we have no empty loops
        return True
    idle_add (executeQueue)
    
        ########################################################################
        # Initialize Seek List                                                 #
        ########################################################################
    
    def addColumns (treeview, *columns):
        for i, name in enumerate(columns):
            column = gtk.TreeViewColumn(name, gtk.CellRendererText(), text=i)
            column.set_sort_column_id(i)
            treeview.append_column(column)
    
    tv = widgets["seektreeview"]
    sstore = gtk.ListStore(str, int, str, str, str)
    tv.set_model(gtk.TreeModelSort(sstore))
    addColumns(tv, "Name", "Rating", "Rated", "Type", "Clock")
    
    seeks = {}
    
    def on_seek_add (manager, seek):
        def call ():
            time = "%s min + %s sec" % (seek["t"], seek["i"])
            ti = sstore.append (
                [seek["w"], int(seek["rt"]), seek["r"], seek["tp"], time])
            seeks [seek["gameno"]] = ti
        listqueue.put(call)
    glm.connect("addSeek", on_seek_add)
    
    def on_seek_remove (manager, gameno):
        def call ():
            if not gameno in seeks:
                # We ignore removes we haven't added, as it seams fics sends a
                # lot of removes for games it has never told us about
                return
            ti = seeks [gameno]
            if not sstore.iter_is_valid(ti):
                return
            sstore.remove (ti)
            del seeks[gameno]
        listqueue.put(call)
    glm.connect("removeSeek", on_seek_remove)
    
    def on_seek_clear (manager):
        def call ():
            sstore.clear()
            seeks.clear()
        listqueue.put(call)
    glm.connect("clearSeeks", on_seek_clear)
    
        ########################################################################
        # Initialize Seek Graph                                                #
        ########################################################################
    
    graph = SpotGraph()
    widgets["graphDock"].add(graph)
    graph.show()
    
    def on_seek_add (manager, seek):
        def call ():
            # The lower the -8 number, the steeper the acceleration
            x = e**(-8/(float(seek["t"])+float(seek["i"])/3))
            y = seek["rt"].isdigit() and float(seek["rt"])/3000 or 0
            type = seek["r"] == "u" and 1 or 0
            graph.addSpot(seek["gameno"], x, y, type)
        listqueue.put(call)
    glm.connect("addSeek", on_seek_add)
    
    def on_seek_remove (manager, gameno):
        def call ():
            graph.removeSpot(gameno)
        listqueue.put(call)
    glm.connect("removeSeek", on_seek_remove)
    
    def on_seek_clear (manager):
        def call ():
            graph.clearSpots()
        listqueue.put(call)
    glm.connect("clearSeeks", on_seek_clear)
    
        ########################################################################
        # Initialize Players List                                              #
        ########################################################################
    
    tv = widgets["playertreeview"]
    pstore = gtk.ListStore(str, int)
    tv.set_model(gtk.TreeModelSort(pstore))
    addColumns(tv, "Name", "Rating")
    tv.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
    
    players = {}
    
    def on_player_add (manager, player):
        def call ():
            rating = player["r"].isdigit() and int(player["r"]) or 0
            ti = pstore.append ([ player["name"], rating ])
            players [player["name"]] = ti
        listqueue.put(call)
    glm.connect("addPlayer", on_player_add)
    
    def on_player_remove (manager, name):
        def call ():
            if not name in players:
                return
            ti = players [name]
            if not pstore.iter_is_valid(ti):
                return
            pstore.remove (ti)
            del players[name]
        listqueue.put(call)
    glm.connect("removePlayer", on_player_remove)
    
        ########################################################################
        # Initialize Games List                                                #
        ########################################################################
    
    tv = widgets["gametreeview"]
    gstore = gtk.ListStore(str, str)
    tv.set_model(gtk.TreeModelSort(gstore))
    addColumns(tv, "White", "Black")
    
    games = {}
    
    def on_game_add (manager, game):
        def call ():
            ti = gstore.append ([ game["wn"], game["bn"] ])
            games [game["gameno"]] = ti
        listqueue.put(call)
    glm.connect("addGame", on_game_add)
    
    def on_game_remove (manager, gameno):
        def call ():
            if not gameno in games:
                return
            ti = games [gameno]
            if not gstore.iter_is_valid(ti):
                return
            gstore.remove (ti)
            del games[gameno]
        listqueue.put(call)
    glm.connect("removeGame", on_game_remove)

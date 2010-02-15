import os
import webbrowser
import math
import atexit
import signal

import gobject, gtk
from gtk import DEST_DEFAULT_MOTION, DEST_DEFAULT_HIGHLIGHT, DEST_DEFAULT_DROP

from pychess.System import conf, glock, uistuff, prefix, SubProcess
from pychess.System.uistuff import POSITION_NONE, POSITION_CENTER, POSITION_GOLDEN
from pychess.System.Log import log
from pychess.Utils.const import HINT, NAME, SPY, VERSION, VERSION_NAME
from pychess.Utils import book # Kills pychess if no sqlite available
from pychess.widgets import newGameDialog
from pychess.widgets import tipOfTheDay
from pychess.widgets import LogDialog
from pychess.widgets.discovererDialog import DiscovererDialog
from pychess.widgets import gamewidget
from pychess.widgets import gamenanny
from pychess.widgets import ionest
from pychess.widgets import preferencesDialog, gameinfoDialog, playerinfoDialog
from pychess.widgets.TaskerManager import TaskerManager
from pychess.widgets.TaskerManager import NewGameTasker
from pychess.widgets.TaskerManager import InternetGameTasker
from pychess.Players.engineNest import discoverer
from pychess.ic import ICLogon

################################################################################
# gameDic - containing the gamewidget:gamemodel of all open games              #
################################################################################
gameDic = {}
chessFiles = {}

class GladeHandlers:
    
    def on_gmwidg_created (handler, gmwidg, gamemodel):
        gameDic[gmwidg] = gamemodel
        
        # Bring playing window to the front
        gamewidget.getWidgets()["window1"].present()
        
        # Make sure we can remove gamewidgets from gameDic later
        gmwidg.connect("closed", GladeHandlers.__dict__["on_gmwidg_closed"])
    
    def on_gmwidg_closed (gmwidg):
        del gameDic[gmwidg]
        if not gameDic:
            for widget in gamewidget.MENU_ITEMS:
                gamewidget.getWidgets()[widget].set_property('sensitive', False)
    
    #          Drag 'n' Drop          #
    
    def on_drag_received (wi, context, x, y, selection, target_type, timestamp):
        uri = selection.data.strip()
        uris = uri.split()
        if len(uris) > 1:
            log.warn("%d files were dropped. Only loading the first" % len(uris))
        uri = uris[0]
        newGameDialog.LoadFileExtension.run(uri)
    
    #          Game Menu          #
    
    def on_new_game1_activate (widget):
        newGameDialog.NewGameMode.run()
    
    def on_play_internet_chess_activate (widget):
        ICLogon.run()
    
    def on_load_game1_activate (widget):
        newGameDialog.LoadFileExtension.run(None, chessFiles)
    
    def on_set_up_position_activate (widget):
        # Not implemented
        pass
    
    def on_enter_game_notation_activate (widget):
        newGameDialog.EnterNotationExtension.run()
    
    def on_save_game1_activate (widget):
        ionest.saveGame (gameDic[gamewidget.cur_gmwidg()])
    
    def on_save_game_as1_activate (widget):
        ionest.saveGameAs (gameDic[gamewidget.cur_gmwidg()])
    
    def on_properties1_activate (widget):
        gameinfoDialog.run(gamewidget.getWidgets(), gameDic)
    
    def on_player_rating1_activate (widget):
        playerinfoDialog.run(gamewidget.getWidgets())
    
    def on_close1_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        response = ionest.closeGame(gmwidg, gameDic[gmwidg])
    
    def on_quit1_activate (widget, *args):
        if ionest.closeAllGames(gameDic.items()) in (gtk.RESPONSE_OK, gtk.RESPONSE_YES):
            gtk.main_quit()
        else: return True
    
    #          View Menu          #
    
    def on_rotate_board1_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        if gmwidg.board.view.rotation:
            gmwidg.board.view.rotation = 0
        else:
            gmwidg.board.view.rotation = math.pi

    
    def on_fullscreen1_activate (widget):
        gamewidget.getWidgets()["window1"].fullscreen()
        gamewidget.getWidgets()["fullscreen1"].hide()
        gamewidget.getWidgets()["leave_fullscreen1"].show()
    
    def on_leave_fullscreen1_activate (widget):
        gamewidget.getWidgets()["window1"].unfullscreen()
        gamewidget.getWidgets()["leave_fullscreen1"].hide()
        gamewidget.getWidgets()["fullscreen1"].show()
    
    def on_about1_activate (widget):
        gamewidget.getWidgets()["aboutdialog1"].show()
    
    def on_log_viewer1_activate (widget):
        if widget.get_active():
            LogDialog.show()
        else: LogDialog.hide()
    
    def on_show_sidepanels_activate (widget):
        gamewidget.zoomToBoard(not widget.get_active())
    
    def on_hint_mode_activate (widget):
        for gmwidg in gameDic.keys():
            gamenanny.setAnalyzerEnabled(gmwidg, HINT, widget.get_active())
    
    def on_spy_mode_activate (widget):
        for gmwidg in gameDic.keys():
            print "setting spymode for", gmwidg, "to", widget.get_active()
            gamenanny.setAnalyzerEnabled(gmwidg, SPY, widget.get_active())
    
    #          Settings menu          #
    
    def on_preferences_activate (widget):
        preferencesDialog.run(gamewidget.getWidgets())
    
    #          Help menu          #
    
    def on_about_chess1_activate (widget):
        webbrowser.open(_("http://en.wikipedia.org/wiki/Chess"))
    
    def on_how_to_play1_activate (widget):
        webbrowser.open(_("http://en.wikipedia.org/wiki/Rules_of_chess"))

    def translate_this_application_activate(widget):
        webbrowser.open("http://code.google.com/p/pychess/wiki/RosettaTranslates")
        
    def on_TipOfTheDayMenuItem_activate (widget):
        tipOfTheDay.TipOfTheDay.show()
    
    #          Other          #
    
    def on_notebook2_switch_page (widget, page, page_num):
        gamewidget.getWidgets()["notebook3"].set_current_page(page_num)
    


dnd_list = [ ('application/x-chess-pgn', 0, 0xbadbeef),
             ('application/da-chess-pgn', 0, 0xbadbeef),
             ('text/plain', 0, 0xbadbeef) ]


class PyChess:
    def __init__(self, args):
        self.initGlade()
        self.handleArgs(args)
    
    def initGlade(self):
        #=======================================================================
        # Init glade and the 'GladeHandlers'
        #=======================================================================
        gtk.glade.set_custom_handler(self.widgetHandler)
        widgets = uistuff.GladeWidgets("PyChess.glade")
        widgets.getGlade().signal_autoconnect(GladeHandlers.__dict__)
        
        #------------------------------------------------------ Redirect widgets
        gamewidget.setWidgets(widgets)
        
        #-------------------------- Main.py still needs a minimum of information
        ionest.handler.connect("gmwidg_created",
                               GladeHandlers.__dict__["on_gmwidg_created"])
        
        #---------------------- The only menuitems that need special initing
        uistuff.keep(widgets["hint_mode"], "hint_mode")
        uistuff.keep(widgets["spy_mode"], "spy_mode")
        uistuff.keep(widgets["show_sidepanels"], "show_sidepanels")
        
        #=======================================================================
        # Show main window and init d'n'd
        #=======================================================================
        uistuff.keepWindowSize("main", widgets["window1"], (575,479), POSITION_GOLDEN)
        widgets["window1"].show()
        widgets["Background"].show_all()
        
        flags = DEST_DEFAULT_MOTION | DEST_DEFAULT_HIGHLIGHT | DEST_DEFAULT_DROP
        widgets["menubar1"].drag_dest_set(flags, dnd_list, gtk.gdk.ACTION_COPY)
        widgets["Background"].drag_dest_set(flags, dnd_list, gtk.gdk.ACTION_COPY)
        
        #=======================================================================
        # Init 'minor' dialogs
        #=======================================================================
        
        #------------------------------------------------------------ Log dialog
        LogDialog.add_destroy_notify(lambda: widgets["log_viewer1"].set_active(0))
        
        #---------------------------------------------------------- About dialog
        clb = widgets["aboutdialog1"].get_child().get_children()[1].get_children()[2]
        widgets["aboutdialog1"].set_name(NAME)
        if os.path.isfile(prefix.addDataPrefix(".svn/entries")):
            f = open(prefix.addDataPrefix(".svn/entries"))
            line4 = [f.next() for i in xrange(4)][-1].strip()
            widgets["aboutdialog1"].set_version(VERSION_NAME+" r"+line4)
        else:
            widgets["aboutdialog1"].set_version(VERSION_NAME+" "+VERSION)
        def callback(button, *args):
            widgets["aboutdialog1"].hide()
            return True
        clb.connect("activate", callback)
        clb.connect("clicked", callback)
        widgets["aboutdialog1"].connect("delete-event", callback)
        
        #----------------------------------------------------- Discoverer dialog
        def discovering_started (discoverer, binnames):
            gobject.idle_add(DiscovererDialog.show, discoverer, binnames, widgets["window1"])
            #DiscovererDialog.show(discoverer, binnames, widgets["window1"])
        discoverer.connect("discovering_started", discovering_started)
        #glock.glock_connect(discoverer, "discovering_started", discovering_started)
        #gobject.idle_add(discoverer.start)
        discoverer.start()
        
        #------------------------------------------------- Tip of the day dialog
        if conf.get("show_tip_at_startup", False):
            tipOfTheDay.TipOfTheDay.show()
    
    
    def widgetHandler (self, glade, functionName, widgetName, s1, s2, i1, i2):
        # Tasker is currently the only widget that uses glades CustomWidget
        tasker = TaskerManager()
        tasker.packTaskers (NewGameTasker(), InternetGameTasker())
        return tasker
    
    def handleArgs (self, args):
        if args:
            def do (discoverer):
                newGameDialog.LoadFileExtension.run(args[0], chessFiles)
            glock.glock_connect_after(discoverer, "all_engines_discovered", do)

def run (args):
    PyChess(args)
    signal.signal(signal.SIGINT, gtk.main_quit)
    def cleanup ():
        SubProcess.finishAllSubprocesses()
    atexit.register(cleanup)
    gtk.gdk.threads_init()
    gtk.main()

import os
import webbrowser
import math
import atexit
import signal
import urllib 
from urlparse import urlparse

import gobject, gtk
from gtk import DEST_DEFAULT_MOTION, DEST_DEFAULT_HIGHLIGHT, DEST_DEFAULT_DROP

from pychess.System import conf, glock, uistuff, prefix, SubProcess, Log, ThreadPool
from pychess.System.uistuff import POSITION_NONE, POSITION_CENTER, POSITION_GOLDEN
from pychess.System.Log import log, start_thread_dump
from pychess.Utils.const import HINT, NAME, SPY
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
from pychess.Savers import png
from pychess.ic import ICLogon
#from pychess.Database.gamelist import GameList
from pychess import VERSION, VERSION_NAME

################################################################################
# gameDic - containing the gamewidget:gamemodel of all open games              #
################################################################################
gameDic = {}

########################
#  For Racent Chooser 
########################
recentManager = gtk.recent_manager_get_default()


class GladeHandlers:
    
    def on_window_key_press (window, event):
        # Tabbing related shortcuts
        if not gamewidget.getheadbook():
            pagecount = 0
        else: pagecount = gamewidget.getheadbook().get_n_pages()
        if pagecount > 1:
            if event.state & gtk.gdk.CONTROL_MASK:
                page_num = gamewidget.getheadbook().get_current_page()
                # Move selected
                if event.state & gtk.gdk.SHIFT_MASK:
                    child = gamewidget.getheadbook().get_nth_page(page_num)
                    if event.keyval == gtk.keysyms.Page_Up:
                        gamewidget.getheadbook().reorder_child(child, (page_num-1)%pagecount)
                    elif event.keyval == gtk.keysyms.Page_Down:
                        gamewidget.getheadbook().reorder_child(child, (page_num+1)%pagecount)
                # Change selected
                else:
                    if event.keyval == gtk.keysyms.Page_Up:
                        gamewidget.getheadbook().set_current_page((page_num-1)%pagecount)
                    elif event.keyval == gtk.keysyms.Page_Down:
                        gamewidget.getheadbook().set_current_page((page_num+1)%pagecount)
        # Other
        pass
    
    def on_gmwidg_created (handler, gmwidg, gamemodel):
        gameDic[gmwidg] = gamemodel
        
        # Bring playing window to the front
        gamewidget.getWidgets()["window1"].present()

        gamemodel.connect("game_loaded", GladeHandlers.__dict__["on_recent_game_activated"])
        gamemodel.connect("game_saved", GladeHandlers.__dict__["on_recent_game_activated"])
        
        # Make sure we can remove gamewidgets from gameDic later
        gmwidg.connect("closed", GladeHandlers.__dict__["on_gmwidg_closed"])

    def on_recent_game_activated (gamemodel, uri):
        if isinstance(uri, basestring):
            o = urlparse(uri)
            recent_data = {
                'mime_type':'application/x-chess-pgn',
                'app_name':'pychess',
                'app_exec':'pychess',
                'group':'pychess'}
            recentManager.add_full("file://" + o.path, recent_data)
    
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
        newGameDialog.LoadFileExtension.run(None)
    
    def on_set_up_position_activate (widget):
        # Not implemented
        pass

    #def on_open_database_activate (widget):
        #GameList().load_games()
    
    def on_enter_game_notation_activate (widget):
        newGameDialog.EnterNotationExtension.run()
    
    def on_save_game1_activate (widget):
        ionest.saveGame (gameDic[gamewidget.cur_gmwidg()])
    
    def on_save_game_as1_activate (widget):
        ionest.saveGameAs (gameDic[gamewidget.cur_gmwidg()])

    def on_export_position_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        png.export(gmwidg, gameDic[gmwidg])
    
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
            if gmwidg.isInFront():
                if widget.get_active():
                    gmwidg.gamemodel.resume_analyzer(HINT)
                else:
                    gmwidg.gamemodel.pause_analyzer(HINT)
    
    def on_spy_mode_activate (widget):
        for gmwidg in gameDic.keys():
            if gmwidg.isInFront():
                if widget.get_active():
                    gmwidg.gamemodel.resume_analyzer(SPY)
                else:
                    gmwidg.gamemodel.pause_analyzer(SPY)
    
    #          Settings menu          #
    
    def on_preferences_activate (widget):
        preferencesDialog.run(gamewidget.getWidgets())
    
    #          Help menu          #
    
    def on_about_chess1_activate (widget):
        webbrowser.open(_("http://en.wikipedia.org/wiki/Chess"))
    
    def on_how_to_play1_activate (widget):
        webbrowser.open(_("http://en.wikipedia.org/wiki/Rules_of_chess"))

    def translate_this_application_activate(widget):
        webbrowser.open("http://code.google.com/p/pychess/wiki/TransifexTranslates")
        
    def on_TipOfTheDayMenuItem_activate (widget):
        tipOfTheDay.TipOfTheDay.show()
    
    #          Other          #
    
    def on_notebook2_switch_page (widget, page, page_num):
        gamewidget.getWidgets()["notebook3"].set_current_page(page_num)
    


dnd_list = [ ('application/x-chess-pgn', 0, 0xbadbeef),
             ('application/da-chess-pgn', 0, 0xbadbeef),
             ('text/plain', 0, 0xbadbeef) ]


class PyChess:
    def __init__(self, chess_file):
        self.initGlade()
        self.handleArgs(chess_file)
    
    def initGlade(self):
        #=======================================================================
        # Init glade and the 'GladeHandlers'
        #=======================================================================
        gtk.glade.set_custom_handler(self.widgetHandler)
        gtk.about_dialog_set_url_hook(self.website)
        widgets = uistuff.GladeWidgets("PyChess.glade")
        widgets.getGlade().signal_autoconnect(GladeHandlers.__dict__)
        
        #------------------------------------------------------ Redirect widgets
        gamewidget.setWidgets(widgets)
        
        def on_sensitive_changed (widget, prop):
            name = widget.get_property('name')
            sensitive = widget.get_property('sensitive')
            #print "'%s' changed to '%s'" % (name, sensitive)
        widgets['pause1'].connect("notify::sensitive", on_sensitive_changed)
        widgets['resume1'].connect("notify::sensitive", on_sensitive_changed)
        #-------------------------- Main.py still needs a minimum of information
        ionest.handler.connect("gmwidg_created",
                               GladeHandlers.__dict__["on_gmwidg_created"])
        
        #---------------------- The only menuitems that need special initing
        for widget in ("hint_mode", "spy_mode"):
            widgets[widget].set_sensitive(False)
        uistuff.keep(widgets["show_sidepanels"], "show_sidepanels")
        
        #=======================================================================
        # Show main window and init d'n'd
        #=======================================================================
        widgets["window1"].set_title('%s - PyChess' % _('Welcome'))
        widgets["window1"].connect("key-press-event",
                                   GladeHandlers.__dict__["on_window_key_press"])
        uistuff.keepWindowSize("main", widgets["window1"], (575,479), POSITION_GOLDEN)
        widgets["window1"].show()
        widgets["Background"].show_all()
        
        flags = DEST_DEFAULT_MOTION | DEST_DEFAULT_HIGHLIGHT | DEST_DEFAULT_DROP
        # To get drag in the whole window, we add it to the menu and the
        # background. If it can be gotten to work, the drag_dest_set_proxy
        # method is very interesting.
        widgets["menubar1"].drag_dest_set(flags, dnd_list, gtk.gdk.ACTION_COPY)
        widgets["Background"].drag_dest_set(flags, dnd_list, gtk.gdk.ACTION_COPY)
        # The following two should really be set in the glade file
        widgets["menubar1"].set_events(widgets["menubar1"].get_events() | gtk.gdk.DRAG_STATUS)
        widgets["Background"].set_events(widgets["Background"].get_events() | gtk.gdk.DRAG_STATUS)
        
        #=======================================================================
        # Init 'minor' dialogs
        #=======================================================================
        
        #------------------------------------------------------------ Log dialog
        LogDialog.add_destroy_notify(lambda: widgets["log_viewer1"].set_active(0))
        
        #---------------------------------------------------------- About dialog
        clb = widgets["aboutdialog1"].get_child().get_children()[1].get_children()[2]
        widgets["aboutdialog1"].set_name(NAME)
        #widgets["aboutdialog1"].set_position(gtk.WIN_POS_CENTER)
        #widgets["aboutdialog1"].set_website_label(_("PyChess Homepage"))
        link = widgets["aboutdialog1"].get_website()
        if os.path.isfile(prefix.addDataPrefix(".svn/entries")):
            f = open(prefix.addDataPrefix(".svn/entries"))
            line4 = [f.next() for i in xrange(4)][-1].strip()
            widgets["aboutdialog1"].set_version(VERSION_NAME+" r"+line4)
        else:
            widgets["aboutdialog1"].set_version(VERSION_NAME+" "+VERSION)
        
        with open(prefix.addDataPrefix("ARTISTS")) as f:
            widgets["aboutdialog1"].set_artists(f.read().splitlines())
        with open(prefix.addDataPrefix("AUTHORS")) as f:
            widgets["aboutdialog1"].set_authors(f.read().splitlines())
        with open(prefix.addDataPrefix("DOCUMENTERS")) as f:
            widgets["aboutdialog1"].set_documenters(f.read().splitlines())
        with open(prefix.addDataPrefix("TRANSLATORS")) as f:
            widgets["aboutdialog1"].set_translator_credits(f.read())

        def callback(button, *args):
            widgets["aboutdialog1"].hide()
            return True
        clb.connect("activate", callback)
        clb.connect("clicked", callback)
        widgets["aboutdialog1"].connect("delete-event", callback)

        #---------------------------------------------------- RecentChooser
        def recent_item_activated (self):
            uri = self.get_current_uri()
            try:
                urllib.urlopen(uri).close()
                newGameDialog.LoadFileExtension.run(self.get_current_uri())
            except (IOError, OSError):
                #shomething wrong whit the uri
                recentManager.remove_item(uri)
                
        self.menu_recent = gtk.RecentChooserMenu(recentManager)
        self.menu_recent.set_show_tips(True)
        self.menu_recent.set_sort_type(gtk.RECENT_SORT_MRU)
        self.menu_recent.set_limit(10)
        self.menu_recent.set_name("menu_recent")
        
        self.file_filter = gtk.RecentFilter()
        self.file_filter.add_mime_type("application/x-chess-pgn")
        self.menu_recent.set_filter(self.file_filter)

        self.menu_recent.connect("item-activated", recent_item_activated)
        widgets["load_recent_game1"].set_submenu(self.menu_recent)
        
        #----------------------------------------------------- Discoverer dialog
        def discovering_started (discoverer, binnames):
            gobject.idle_add(DiscovererDialog.show, discoverer, widgets["window1"])
        discoverer.connect("discovering_started", discovering_started)
        DiscovererDialog.init(discoverer)
        discoverer.start()
        
        #------------------------------------------------- Tip of the day dialog
        if conf.get("show_tip_at_startup", False):
            tipOfTheDay.TipOfTheDay.show()

    def website(self, clb, link):
        webbrowser.open(link)
    
    def widgetHandler (self, glade, functionName, widgetName, s1, s2, i1, i2):
        # Tasker is currently the only widget that uses glades CustomWidget
        tasker = TaskerManager()
        tasker.packTaskers (NewGameTasker(), InternetGameTasker())
        return tasker
    
    def handleArgs (self, chess_file):
        if chess_file:
            def do (discoverer):
                newGameDialog.LoadFileExtension.run(chess_file)
            glock.glock_connect_after(discoverer, "all_engines_discovered", do)

def run (no_debug, glock_debug, thread_debug, stack_tracer, chess_file):
    PyChess(chess_file)
    signal.signal(signal.SIGINT, gtk.main_quit)
    def cleanup ():
        SubProcess.finishAllSubprocesses()
    atexit.register(cleanup)
    gtk.gdk.threads_init()
    
    # Start logging
    Log.DEBUG = False if no_debug is True else True
    glock.debug = glock_debug
    ThreadPool.debug = stack_tracer
    log.debug("Started\n")
    if thread_debug:
        start_thread_dump()
    
    gtk.main()

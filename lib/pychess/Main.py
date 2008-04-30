import sys
import webbrowser
import math
import atexit
import signal

import pango, gobject, gtk

from pychess.System import conf, gstreamer, glock, uistuff
from pychess.System.prefix import addDataPrefix
from pychess.System.Log import log
from pychess.System.GtkWorker import GtkWorker
from pychess.Utils.const import *
from pychess.Utils import book # Kills pychess if no sqlite available
from pychess.Utils.GameModel import GameModel
from pychess.Utils.TimeModel import TimeModel
from pychess.Players.Human import Human
from pychess.Players.engineNest import discoverer
from pychess.widgets import newGameDialog
from pychess.widgets import tipOfTheDay
from pychess.widgets import LogDialog
from pychess.widgets import gamewidget
from pychess.widgets.gamewidget import GAME_MENU_ITEMS, ACTION_MENU_ITEMS
from pychess.widgets.gamewidget import VIEW_MENU_ITEMS, MENU_ITEMS
from pychess.widgets import ionest
from pychess.widgets import preferencesDialog, gameinfoDialog, playerinfoDialog
from pychess.widgets.Background import TaskerManager
from pychess.widgets.Background import NewGameTasker
from pychess.widgets.Background import InternetGameTasker
from pychess.ic import ICLogon

################################################################################
# gameDic - containing the gamewidget:gamemodel of all open games              #
################################################################################
gameDic = {}

def engineDead (engine, gmwidg):
    glock.acquire()
    try:
        gmwidg.bringToFront()
        d = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
        d.set_markup(_("<big><b>Engine, %s, has died</b></big>") % repr(engine))
        d.format_secondary_text(_("PyChess has lost connection to the engine, probably because it has died.\n\nYou can try to start a new game with the engine, or try to play against another one."))
        d.connect("response", lambda d,r: d.hide())
        d.show_all()
    finally:
        glock.release()

def makeLogDialogReady ():
    LogDialog.add_destroy_notify(lambda: window["log_viewer1"].set_active(0))

def makeAboutDialogReady ():
    clb = window["aboutdialog1"].get_child().get_children()[1].get_children()[2]
    window["aboutdialog1"].set_version(VERSION_NAME+" "+VERSION)
    def callback(button, *args):
        window["aboutdialog1"].hide()
        return True
    clb.connect("activate", callback)
    clb.connect("clicked", callback)
    window["aboutdialog1"].connect("delete-event", callback)

def setMode (gmwidg, mode, activated):
    if not gameDic: return
    
    gamemodel = gameDic[gmwidg]
    board = gmwidg.board
    
    if not mode in gamemodel.spectactors: return
    analyzer = gamemodel.spectactors[mode]
    
    if mode == HINT:
        arrow = board.view._set_greenarrow
    else: arrow = board.view._set_redarrow
    set_arrow = lambda x: board.view.runWhenReady(arrow, x)
    
    if activated:
        if len(analyzer.analyzeMoves) >= 1:
            if gamemodel.curplayer.__type__ == LOCAL:
                set_arrow (analyzer.analyzeMoves[0].cords)
            else: set_arrow (None)
        
        # This is a kludge using pythons ability to asign attributes to an
        # object, even if those attributes are nowhere mentioned in the objects
        # class. So don't go looking for it ;)
        # Code is used to save our connection ids, enabling us to later dis-
        # connect
        if not hasattr (gamemodel, "anacons"):
            gamemodel.anacons = {HINT:[], SPY:[]}
        if not hasattr (gamemodel, "chacons"):
            gamemodel.chacons = []
        
        def on_analyze (analyzer, moves):
            if gamemodel.curplayer.__type__ == LOCAL and moves:
               set_arrow (moves[0].cords)
            else: set_arrow (None)
            
        def on_game_change (gamemodel):
            set_arrow (None)
        
        gamemodel.anacons[mode].append(
                analyzer.connect("analyze", on_analyze))
        gamemodel.chacons.append(
                gamemodel.connect("game_changed", on_game_change))
    
    else:
        if hasattr (gamemodel, "anacons"):
            for conid in gamemodel.anacons[mode]:
                analyzer.disconnect(conid)
            del gamemodel.anacons[mode][:]
        if hasattr (gamemodel, "chacons"):
            for conid in gamemodel.chacons:
                gamemodel.disconnect(conid)
            del gamemodel.chacons[:]
        set_arrow (None)

class GladeHandlers:
    
    def on_gmwidg_created (handler, gmwidg, gamemodel):
        gameDic[gmwidg] = gamemodel
        
        # Make sure game dependent menu entries are sensitive
        for widget in MENU_ITEMS:
            window[widget].set_property('sensitive', True)
        
        # Disable hint or spy menu, if they are disabled in preferences
        window["hint_mode"].set_sensitive(conf.get("analyzer_check", True))
        window["spy_mode"].set_sensitive(conf.get("inv_analyzer_check", True))
        
        # Bring playing window to the front
        window["window1"].present()
        
        setMode(gmwidg, HINT, window["hint_mode"].get_active())
        setMode(gmwidg, SPY, window["spy_mode"].get_active())
        
        # Connect game_loaded, game_saved and game_ended to statusbar
        def game_loaded (gamemodel, uri):
            if type(uri) in (str, unicode):
                s = "%s: %s" % (_("Loaded game"), str(uri))
            else: s = _("Loaded game")
            gmwidg.status(s)
        gamemodel.connect("game_loaded", game_loaded)
        
        def game_saved (gamemodel, uri):
            gmwidg.status("%s: %s" % (_("Saved game"), str(uri)))
        gamemodel.connect("game_saved", game_saved)
        
        def game_ended (gamemodel, reason):
            m1 = {
                DRAW: _("The game ended in a draw"),
                WHITEWON: _("White player won the game"),
                BLACKWON: _("Black player won the game"),
                KILLED: _("The game has been killed"),
                ADJOURNED: _("The game has been adjourned"),
                ABORTED: _("The game has been aborted"),
            }[gamemodel.status]
            m2 = {
                DRAW_INSUFFICIENT: _("caused by insufficient material"),
                DRAW_REPITITION: _("as the same position was repeated three times in a row"),
                DRAW_50MOVES: _("as the last 50 moves brought nothing new"),
                DRAW_CALLFLAG: _("as both players ran out of time"),
                DRAW_STALEMATE: _("because of stalemate"),
                DRAW_AGREE: _("as the players agreed to"),
                DRAW_ADJUDICATION: _("as decided by an admin"),
                DRAW_LENGTH: _("as game exceed the max length"),
                
                WON_RESIGN: _("as opponent resigned"),
                WON_CALLFLAG: _("as opponent ran out of time"),
                WON_MATE: _("on a mate"),
                WON_DISCONNECTION: _("as opponent disconnected"),
                WON_ADJUDICATION:  _("as decided by an admin"),
                
                ADJOURNED_LOST_CONNECTION: _("as a player lost connection"),
                ADJOURNED_AGREEMENT: _("as the players agreed to"),
                ADJOURNED_SERVER_SHUTDOWN: _("as the server was shut down"),
                
                ABORTED_ADJUDICATION: _("as decided by an admin"),
                ABORTED_AGREEMENT: _("as the players agreed to"),
                ABORTED_COURTESY: _("by courtesy by a player"),
                ABORTED_EARLY: _("in the early phase of the game"),
                ABORTED_SERVER_SHUTDOWN: _("as the server was shut down"),
                
                WHITE_ENGINE_DIED: _("as the white engine died"),
                BLACK_ENGINE_DIED: _("as the black engine died"),
                UNKNOWN_REASON: _("by no known reason")
            }[reason]
            gmwidg.status("%s %s" % (m1,m2))
            
            if reason == WHITE_ENGINE_DIED:
                engineDead(gamemodel.players[0], gmwidg)
            elif reason == BLACK_ENGINE_DIED:
                engineDead(gamemodel.players[1], gmwidg)
        gamemodel.connect("game_ended", game_ended)
        
        def on_game_started (gamemodel):
            # Rotate to human player
            boardview = gmwidg.board.view
            if gamemodel.players[1].__type__ == LOCAL:
                if gamemodel.players[0].__type__ != LOCAL:
                    boardview.rotation = math.pi
                elif conf.get("autoRotate", True) and \
                        gamemodel.curplayer == gamemodel.players[1]:
                    boardview.rotation = math.pi
            
            # Play set-up sound
            if conf.get("useSounds", False):
                preferencesDialog.SoundTab.playAction("gameIsSetup")
            
            # Connect player offers to statusbar
            for player in gamemodel.players:
                if player.__type__ == LOCAL:
                    def offer_callback (player, offer):
                        if offer.offerType == DRAW_OFFER:
                            if gamemodel.status != RUNNING:
                                return # If the offer has already been handled by
                                       # Gamemodel and the game was drawn, we need
                                       # to do nothing
                            glock.acquire()
                            try:
                                gmwidg.status(_("You sent a draw offer"))
                            finally:
                                glock.release()
                    player.connect("offer", offer_callback)
            
            def on_gmwidg_closed (gmwidg):
                del gameDic[gmwidg]
                for player in gamemodel.players:
                    player.kill(WON_DISCONNECTION)
                if not gameDic:
                    for widget in MENU_ITEMS:
                        window[widget].set_property('sensitive', False)
            gmwidg.connect("closed", on_gmwidg_closed)
            
            # Set right sensitivity states in menubar, when tab is switched
            def infront (gmwidg):
                auto = gamemodel.players[0].__type__ != LOCAL and \
                        gamemodel.players[1].__type__ != LOCAL
                for widget in ACTION_MENU_ITEMS:
                    window[widget].props.sensitive = not auto
            gmwidg.connect("infront", infront)
            infront(gmwidg)
        
        gamemodel.connect("game_started", on_game_started)
    
    #          Drag 'n' Drop          #
    
    def on_drag_received (wi, context, x, y, selection, target_type, timestamp):
        uri = selection.data.strip()
        # We may have more than one file dropped. We choose only to care about
        # the first.
        uri = uri.split()[0]
        def callback (startdata):
            ionest.generalStart(*startdata)
        newGameDialog.LoadFileExtension.run(callback, uri)
    
    #          Game Menu          #
    
    def on_new_game1_activate (widget):
        def callback (startdata):
            ionest.generalStart(*startdata)
        newGameDialog.NewGameMode.run(callback)
    
    def on_play_internet_chess_activate (widget):
        ICLogon.run()
    
    def on_load_game1_activate (widget):
        def callback (startdata):
            ionest.generalStart(*startdata)
        newGameDialog.LoadFileExtension.run(callback)
    
    def on_set_up_position_activate (widget):
        # Not implemented
        pass
    
    def on_enter_game_notation_activate (widget):
        def callback (startdata):
            ionest.generalStart(*startdata)
        newGameDialog.EnterNotationExtension.run(callback)
    
    def on_save_game1_activate (widget):
        ionest.saveGame (gameDic[gamewidget.cur_gmwidg()])
    
    def on_save_game_as1_activate (widget):
        ionest.saveGameAs (gameDic[gamewidget.cur_gmwidg()])
    
    def on_properties1_activate (widget):
        gameinfoDialog.run(window, gameDic)
    
    def on_player_rating1_activate (widget):
        playerinfoDialog.run(window)
    
    def on_close1_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        ionest.closeGame(gmwidg, gameDic[gmwidg])
    
    def on_quit1_activate (widget, *args):
        if ionest.closeAllGames (gameDic.items()) == gtk.RESPONSE_OK:
            gtk.main_quit()
        else: return True
    
    #          View Menu          #
    
    def on_rotate_board1_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        gmwidg.widgets["board"].view.rotation += math.pi
    
    def on_rearrange_panels_activate (widget):
        gamewidget.showGrips(widget.get_active())
    
    def on_about1_activate (widget):
        window["aboutdialog1"].show()
    
    def on_log_viewer1_activate (widget):
        if widget.get_active():
            LogDialog.show()
        else: LogDialog.hide()
    
    def on_hint_mode_activate (widget):
        for gmwidg in gameDic.keys():
            setMode(gmwidg, HINT, widget.get_active())
    
    def on_spy_mode_activate (widget):
        for gmwidg in gameDic.keys():
            setMode(gmwidg, SPY, widget.get_active())
    
    #          Settings menu          #
    
    def on_preferences_activate (widget):
        preferencesDialog.run(window)
    
    #          Help menu          #
    
    def on_about_chess1_activate (widget):
        webbrowser.open(_("http://en.wikipedia.org/wiki/Chess"))
    
    def on_how_to_play1_activate (widget):
        webbrowser.open(_("http://en.wikipedia.org/wiki/Rules_of_chess"))

    def translate_this_application_activate(widget):
        webbrowser.open("http://code.google.com/p/pychess/wiki/RosettaTranslates")
        
    def on_TipOfTheDayMenuItem_activate (widget):
        tipOfTheDay.show()
    
    #          Other          #
    
    def on_notebook2_switch_page (widget, page, page_num):
        window["notebook3"].set_current_page(page_num)
    
    #          Taskers        #
    
    def on_newGameTasker_started (tasker, color, opponent, difficulty):
        gamemodel = GameModel(TimeModel(5*60, 0))
        
        player0tup = (LOCAL, Human, (color, ""), _("Human"))
        if opponent == 0:
            player1tup = (LOCAL, Human, (1-color, ""), _("Human"))
        else:
            engine = discoverer.getEngineN (opponent-1)
            name = discoverer.getName(engine)
            player1tup = (ARTIFICIAL, discoverer.initAndStartEngine,
                    (engine, 1-color, difficulty, 5*60, 0), name)
        
        if color == WHITE:
            ionest.generalStart(gamemodel, player0tup, player1tup)
        else: ionest.generalStart(gamemodel, player1tup, player0tup)
    
    def on_internetTasker_connect (tasker, asGuest, username, password):
        ICLogon.run()
        if not ICLogon.dialog.connection:
            ICLogon.dialog.widgets["logOnAsGuest"].set_active(asGuest)
            ICLogon.dialog.widgets["nameEntry"].set_text(username)
            ICLogon.dialog.widgets["passEntry"].set_text(password)
            ICLogon.dialog.widgets["connectButton"].clicked()

dnd_list = [ ('application/x-chess-pgn', 0, 0xbadbeef),
             ('application/da-chess-pgn', 0, 0xbadbeef),
             ('text/plain', 0, 0xbadbeef) ]
from gtk import DEST_DEFAULT_MOTION, DEST_DEFAULT_HIGHLIGHT, DEST_DEFAULT_DROP

class PyChess:
    def __init__(self, args):
        self.initGlade()
        self.handleArgs(args)
    
    def mainWindowSize (self, window):
        def savePosition (window, *event):
            conf.set("window_width",  window.get_allocation().width)
            conf.set("window_height", window.get_allocation().height)
            conf.set("window_x", window.get_position()[0])
            conf.set("window_y", window.get_position()[1])
        window.connect("delete-event", savePosition)
        
        def loadPosition (window):
            width = conf.get("window_width", 575)
            height = conf.get("window_height", 479)
            assert width > 0
            assert height > 0
            window.set_size_request(width, height)
            x = conf.get("window_x", gtk.gdk.screen_width()/2-width/2)
            # As default, put center on upper golden ratio line
            y = conf.get("window_y", int(gtk.gdk.screen_height()/2.618)-height/2)
            window.move(x, y)
        loadPosition(window)
        
        # In rare cases, gtk throws some gtk_size_allocation error, which is
        # probably a race condition. To avoid the window forgets its size in
        # these cases, we add this extra hook
        def callback (window, *args):
            window.disconnect(handle_id)
            loadPosition(window)
            gobject.idle_add(window.set_size_request, -1, -1)
        handle_id = window.connect("size-allocate", callback)
    
    def initGlade(self):
        global window
        window = self
    
        gtk.glade.set_custom_handler(self.widgetHandler)
        self.widgets = gtk.glade.XML(addDataPrefix("glade/PyChess.glade"))
        
        self.widgets.signal_autoconnect(GladeHandlers.__dict__)
        self.mainWindowSize(self["window1"])
        self["window1"].show()
        self["Background"].show_all()
        
        makeLogDialogReady()
        makeAboutDialogReady()
        gamewidget.setWidgets(self)
        ionest.handler.connect("gmwidg_created",
            GladeHandlers.__dict__["on_gmwidg_created"])
        
        flags = DEST_DEFAULT_MOTION | DEST_DEFAULT_HIGHLIGHT | DEST_DEFAULT_DROP
        window["menubar1"].drag_dest_set(flags, dnd_list, gtk.gdk.ACTION_COPY)
        window["Background"].drag_dest_set(flags, dnd_list, gtk.gdk.ACTION_COPY)
        
        #TODO: disabled by default
        #TipOfTheDay.TipOfTheDay()
    
    def __getitem__(self, key):
        return self.widgets.get_widget(key)
    
    def widgetHandler (self, glade, functionName, widgetName, s1, s2, i1, i2):
        # Tasker is currently the only widget that uses glades CustomWidget
        tasker = TaskerManager()
        newGameTasker = NewGameTasker()
        newGameTasker.connect (
            "startClicked", GladeHandlers.__dict__["on_newGameTasker_started"])
        internetGameTasker = InternetGameTasker()
        internetGameTasker.connect (
            "connectClicked", GladeHandlers.__dict__["on_internetTasker_connect"])
        tasker.packTaskers ([newGameTasker, internetGameTasker])
        return tasker
    
    def handleArgs (self, args):
        if args:
            def do ():
                def callback (startdata):
                    ionest.generalStart(*startdata)
                newGameDialog.LoadFileExtension.run(callback, args[0])
                glock.release()
            # For this once we do an idle_add. We do so to ensure the window is
            # set up before we start doing other things
            gobject.idle_add(do)

def run (args):
    PyChess(args)
    signal.signal(signal.SIGINT, gtk.main_quit)
    gtk.gdk.threads_init()
    gtk.main()

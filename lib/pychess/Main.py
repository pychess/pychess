
import os, sys

import pygtk
pygtk.require("2.0")
import sys, gtk, gtk.glade, os
import pango, gobject

import webbrowser
import atexit

from pychess.widgets import ionest
from pychess.System import myconf
from pychess.Utils.const import *
from pychess.Players.Human import Human
from pychess.System.Log import log
from pychess.widgets import tipOfTheDay
from pychess.widgets import LogDialog
from pychess.widgets import gamewidget
from pychess.widgets.Background import Background

from pychess.widgets.ionest import loadGame, newGame, saveGame, saveGameAs

gameDic = {}

def engineDead (engine, gmwidg):
    gamewidget.setCurrent(gmwidg)
    gameDic[gmwidg].kill()
    d = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
    d.set_markup(_("<big><b>Engine, %s, has died</b></big>") % repr(engine))
    d.format_secondary_text(_("PyChess has lost connection to the engine, probably because it has died.\n\nYou can try to start a new game with the engine, or try to play against another one."))
    d.connect("response", lambda d,r: d.hide())
    d.show_all()

def makeLogDialogReady ():
    LogDialog.add_destroy_notify(lambda: window["log_viewer1"].set_active(0))

def makeAboutDialogReady ():
    clb = window["aboutdialog1"].get_child().get_children()[1].get_children()[2]
    window["aboutdialog1"].set_version(VERSION)
    def callback(button, *args):
        window["aboutdialog1"].hide()
        return True
    clb.connect("activate", callback)
    clb.connect("clicked", callback)
    window["aboutdialog1"].connect("delete-event", callback)

def setMode (gmwidg, mode, activated):
    if not gameDic: return
    
    game = gameDic[gmwidg]
    board = gmwidg.widgets["board"]
    history = board.view.history
    analyzer = game.analyzers[mode]
    arrow = mode == HINT and board.view._set_greenarrow or board.view._set_redarrow
    set_arrow = lambda x: board.view.runWhenReady(arrow, x)
    
    if activated:
        if len(analyzer.analyzeMoves) >= 1:
            player = board.view.history.curCol() and game.player2 or game.player1
            if player.__type__ == LOCAL:
                set_arrow (analyzer.analyzeMoves[0].cords)
            else: set_arrow (None)
        
        if not hasattr (game, "anacons"):
            game.anacons = [[],[]]
        if not hasattr (game, "hiscons"):
            game.hiscons = []
        
        def on_analyze (analyzer, moves):
            player = history.curCol() and game.player2 or game.player1
            if player.__type__ == LOCAL:
               set_arrow (moves[0].cords)
            else: set_arrow (None)
            
        def on_clear (history):
            set_arrow (None)
            
        def on_reset (history):
            on_clear (history)
            window[reprMode[mode]+"_mode"].set_active(False)
        
        game.anacons[mode].append ( analyzer.connect("analyze", on_analyze) )
        game.hiscons.append ( history.connect("changed", on_clear) )
        game.hiscons.append ( history.connect("cleared", on_reset) )
    
    else:
        if hasattr (game, "anacons"):
            for conid in game.anacons[mode]:
                analyzer.disconnect(conid)
            del game.anacons[mode][:]
        if hasattr (game, "hiscons"):
            for conid in game.hiscons:
                history.disconnect(conid)
            del game.hiscons[:]
        set_arrow (None)

class GladeHandlers:
    
    def on_ccalign_show (widget):
        clockHeight = window["ccalign"].get_allocation().height
        windowSize = window["window1"].get_size()
        window["window1"].resize(windowSize[0],windowSize[1]+clockHeight)
    
    def on_ccalign_hide (widget):
        clockHeight = window["ccalign"].get_allocation().height
        windowSize = window["window1"].get_size()
        window["window1"].resize(windowSize[0],windowSize[1]-clockHeight)
    
    def on_game_started (handler, gmwidg, game):
        for widget in ("save_game1", "save_game_as1", "properties1",
                       "close1", "action1", "vis1"):
            window[widget].set_property('sensitive', True)
        
        gmwidg.widgets["sidepanel"].connect("hide", \
            lambda w: window["side_panel1"].set_active(False))
        
        gameDic[gmwidg] = game
        
        for player in game.players:
                player.connect("dead", engineDead, gmwidg)
        
        setMode(gmwidg, HINT, window["hint_mode"].get_active())
        setMode(gmwidg, SPY, window["spy_mode"].get_active())
        
    def on_game_closed (handler, gmwidg, game):
        del gameDic[gmwidg]
        
        if len (gameDic) == 0:
            for widget in ("save_game1", "save_game_as1", "properties1",
                           "close1", "action1", "vis1"):
                window[widget].set_property('sensitive', False)
    
    #          Drag 'n' Drop          #
    
    def on_drag_received (wi, context, x, y, selection, target_type, timestamp):
        uri = selection.data.strip()
        # We may have more than one file dropped. We choose only to care about
        # the first.
        uri = uri.split()[0]
        loadGame (uri)
    
    #          Game Menu          #

    def on_new_game1_activate (widget):
        newGame ()
        
    def on_load_game1_activate (widget):
        loadGame ()
    
    def on_save_game1_activate (widget):
        saveGame (gameDic[gamewidget.cur_gmwidg()])
        
    def on_save_game_as1_activate (widget):
        saveGameAs (gameDic[gamewidget.cur_gmwidg()])
    
    def on_properties1_activate (widget):
        game = gameDic[gamewidget.cur_gmwidg()]
        window["event_entry"].set_text(game.event)
        window["site_entry"].set_text(game.site)
        window["round_spinbutton"].set_value(game.round)
        #TODO set the date
        window["game_info"].show()
        def hide_window(button, *args):
            window["game_info"].hide()
            return True
        def accept_new_properties(button, *args):
            game = gameDic[gamewidget.cur_gmwidg()]
            game.event = window["event_entry"].get_text()
            game.site = window["site_entry"].get_text()
            game.round = window["round_spinbutton"].get_value()
            game.year = window["game_info_calendar"].get_date()[0]
            # GtkCalender month goes from 0 to 11
            game.month = window["game_info_calendar"].get_date()[1] + 1
            game.day = window["game_info_calendar"].get_date()[2]
            window["game_info"].hide()
            return True
        window["game_info"].connect("delete-event", hide_window)
        window["game_info_cancel_button"].connect("clicked", hide_window)
        window["game_info_ok_button"].connect("clicked", accept_new_properties)
    
    def on_close1_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        ionest.closeGame(gmwidg, gameDic[gmwidg])
    
    def on_quit1_activate (widget, *args):
        if ionest.closeAllGames (gameDic.values()) == gtk.RESPONSE_OK:
            gtk.main_quit()
        else: return True
    
    #          View Menu          #
    
    def on_rotate_board1_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        gmwidg.widgets["board"].view.fromWhite = \
            not gmwidg.widgets["board"].view.fromWhite
    
    def on_side_panel1_activate (widget):
        gamewidget.show_side_panel(widget.get_active())
    
    def on_show_cords_activate (widget):
        for gmwidg in gameDic.keys():
            gmwidg.widgets["board"].view.showCords = widget.get_active()
    
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
    
    #          Action menu          #
    
    def on_call_flag_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        gmwidg.widgets["board"].on_call_flag_activate (widget)

    def on_draw_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        gmwidg.widgets["board"].on_draw_activate (widget)
        
    def on_resign_activate (widget):
        gmwidg = gamewidget.cur_gmwidg()
        gmwidg.widgets["board"].on_resign_activate (widget)

    def on_force_to_move_activate (widget):
        if len(gameDic):
            gameDic[gamewidget.cur_gmwidg()].activePlayer.hurry()
    
    #          Settings menu          #
    
    def on_preferences2_activate (widget):
        window["preferences"].show()
        def hide_window(button, *args):
            window["preferences"].hide()
            return True
        window["preferences"].connect("delete-event", hide_window)
        window["preferences_close_button"].connect("clicked", hide_window)
    
    #          Help menu          #
    
    def on_about_chess1_activate (widget):
        webbrowser.open(_("http://en.wikipedia.org/wiki/Chess"))
    
    def on_how_to_play1_activate (widget):
        webbrowser.open(_("http://en.wikipedia.org/wiki/Rules_of_chess"))
        
    def on_TipOfTheDayMenuItem_activate (widget):
        tipOfTheDay.show()
    
    #          Other          #
    
    def on_notebook2_switch_page (widget, page, page_num):
        window["notebook3"].set_current_page(page_num)

TARGET_TYPE_URI_LIST = 80
dnd_list = [ ( 'text/plain', 0, TARGET_TYPE_URI_LIST ) ]
from gtk import DEST_DEFAULT_MOTION, DEST_DEFAULT_HIGHLIGHT, DEST_DEFAULT_DROP

class PyChess:
    def __init__(self):
        self.initGlade()
        
    def mainWindowSize (self, window):
        def savePosition ():
            myconf.set("window_width", window.get_allocation().width)
            myconf.set("window_height", window.get_allocation().height)
        atexit.register( savePosition)
        width = myconf.get("window_width")
        height = myconf.get("window_height")
        if width and height:
            window.resize(width, height)
    
    def initGlade(self):
        global window
        window = self
    
        #os.chdir(os.path.abspath(os.path.dirname(__file__)))
        gtk.glade.set_custom_handler(self.widgetHandler)
        self.widgets = gtk.glade.XML(prefix("glade/PyChess.glade"))
        
        self.widgets.signal_autoconnect(GladeHandlers.__dict__)
        self["window1"].show_all()
        
        #Very ugly hack, needed because of pygtk bug 357022
        #http://bugzilla.gnome.org/show_bug.cgi?id=357022
        from widgets.BookCellRenderer import BookCellRenderer
        self.BookCellRenderer = BookCellRenderer
        
        makeLogDialogReady()
        makeAboutDialogReady()
        gamewidget.set_widgets(self)
        ionest.handler.connect("game_started",
            GladeHandlers.__dict__["on_game_started"])
        ionest.handler.connect("game_closed",
            GladeHandlers.__dict__["on_game_closed"])
        
        flags = DEST_DEFAULT_MOTION | DEST_DEFAULT_HIGHLIGHT | DEST_DEFAULT_DROP
        window["menubar1"].drag_dest_set(flags, dnd_list, gtk.gdk.ACTION_COPY)
        window["Background"].drag_dest_set(flags, dnd_list, gtk.gdk.ACTION_COPY)
        
        self.mainWindowSize(self["window1"])
        
        #TODO: disabled by default
        #TipOfTheDay.TipOfTheDay()
    
    def __getitem__(self, key):
        return self.widgets.get_widget(key)
    
    def widgetHandler (self, glade, functionName, widgetName, s1, s2, i1, i2):
        return Background()

def run ():
    PyChess()
    import signal
    signal.signal(signal.SIGINT, gtk.main_quit)
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    gtk.gdk.threads_init()
    gtk.main()

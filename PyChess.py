#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import pygtk
pygtk.require("2.0")
import sys, gtk, gtk.glade, os
import pango, gobject

import random
import webbrowser
import atexit

import gettext
gettext.install("pychess",localedir="lang",unicode=1)
gtk.glade.bindtextdomain("pychess","lang")
gtk.glade.textdomain("pychess")

from Utils.const import *
from Players import engines
from Players.Human import Human
from System import myconf
from System.Log import log
from System import TipOfTheDay
import System.LogDialog
from Game import Game
from widgets import gamewidget


gameDic = {}

def saveGameBefore (action):
    if not window.game: return
    if window.game.history == lastSave[0]: return
    
    defText = window["savedialogtext1"].get_label()
    window["savedialogtext1"].set_markup(defText % action)
    response = window["savegamedialog"].run()
    window["savegamedialog"].hide()
    window["savedialogtext1"].set_markup(defText)
    if response == gtk.RESPONSE_YES:
        if GladeHandlers.__dict__["on_save_game1_activate"](None) == False:
            return gtk.RESPONSE_CANCEL
    return response

def makeFileDialogReady ():
    global enddir

    enddir = {}
    types = []
    savers = ["Savers/"+s for s in os.listdir("Savers")]
    savers = [s[:-3] for s in savers if s.endswith(".py")]
    savers = [s for s in savers if s != "Savers/__init__"]
    for saver in [__import__(s, locals()) for s in savers]:
        for ending in saver.__endings__:
            enddir[ending] = saver
        l = saver.__label__ + " (."+", .".join(saver.__endings__)+")"
        types.append((l, saver.__endings__))
    
    global savedialog, opendialog
    savedialog = gtk.FileChooserDialog(_("Save Game"), None, gtk.FILE_CHOOSER_ACTION_SAVE, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_ACCEPT))
    opendialog = gtk.FileChooserDialog(_("Open Game"), None, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_ACCEPT))
    savedialog.set_current_folder(os.environ["HOME"])
    opendialog.set_current_folder(os.environ["HOME"])
    
    #TODO: Working with mime-types might gennerelly be a better idea.
    
    star = gtk.FileFilter()
    star.set_name(_("All Files"))
    star.add_pattern("*")
    opendialog.add_filter(star)
    
    all = gtk.FileFilter()
    all.set_name(_("All Chess Files"))
    opendialog.add_filter(all)
    opendialog.set_filter(all)
    
    custom = gtk.FileFilter()
    custom.set_name(_("Detect type automatically"))
    custom.add_pattern("*")
    savedialog.add_filter(custom)
    
    for label, endings in types:
        f = gtk.FileFilter()
        f.set_name(label)
        for ending in endings:
            f.add_pattern("*."+ending)
            all.add_pattern("*."+ending)
        savedialog.add_filter(f)
        opendialog.add_filter(f)
    
    global filechooserbutton
    filechooserbutton = gtk.FileChooserButton(opendialog)
    window["ngfcalignment"].add(filechooserbutton)
    filechooserbutton.show()

isMakeNewGameDialogReady = False
def makeNewGameDialogReady ():

    global isMakeNewGameDialogReady
    if isMakeNewGameDialogReady:
        return
    isMakeNewGameDialogReady = True

    def createCombo (combo, data):
        ls = gtk.ListStore(gtk.gdk.Pixbuf, str)
        for icon, label in data:
            ls.append([icon, label])
        combo.clear()
        combo.set_model(ls)
        crp = gtk.CellRendererPixbuf()
        crp.set_property('xalign',0)
        combo.pack_start(crp, False)
        combo.add_attribute(crp, 'pixbuf', 0)
        crt = gtk.CellRendererText()
        crt.set_property('xalign',0)
        combo.pack_start(crt, False)
        combo.add_attribute(crt, 'text', 1)

    it = gtk.icon_theme_get_default()

    icons = ((_("Beginner"), "stock_weather-few-clouds", "weather-few-clouds"), 
             (_("Intermediate"), "stock_weather-cloudy", "weather-overcast"),
             (_("Expert"), "stock_weather-storm", "weather-storm"))
                
    items = []
    for level, stock, altstock in icons:
        try:
            image = it.load_icon(stock, 16, gtk.ICON_LOOKUP_USE_BUILTIN)
        except gobject.GError:
            image = it.load_icon(altstock, 16, gtk.ICON_LOOKUP_USE_BUILTIN)
        items += [(image, level)]

    for combo in (window["whiteDifficulty"], window["blackDifficulty"]):
        createCombo(combo, items)

    image = it.load_icon("stock_people", 24, gtk.ICON_LOOKUP_USE_BUILTIN)
    items = [(image, _("Human Being"))]
    image = it.load_icon("stock_notebook", 24, gtk.ICON_LOOKUP_USE_BUILTIN)
    
    for engine in [engines.getInfo((e,a))["name"] for e,a in engines.availableEngines]:
        items += [(image, engine)]
    for combo in (window["whitePlayerCombobox"], window["blackPlayerCombobox"]):
        createCombo(combo, items)
        
    window["whitePlayerCombobox"].set_active(0)
    window["blackPlayerCombobox"].set_active(min(1,len(engines.availableEngines)))
    GladeHandlers.__dict__['on_blackPlayerCombobox_changed'](window["blackPlayerCombobox"])
    
    for widget in ("whitePlayerCombobox", "blackPlayerCombobox", "whiteDifficulty", "blackDifficulty",
            "spinbuttonH", "spinbuttonM", "spinbuttonS", "spinbuttonG", "useTimeCB"):
        v = myconf.get(widget)
        if v != None:
            if hasattr(window[widget], "set_active"):
                window[widget].set_active(v)
            else: window[widget].set_value(v)
        
def runNewGameDialog (hideFC=True):
    makeNewGameDialogReady ()
    
    if hideFC:
        window["ngfcalignment"].hide()
    else: window["ngfcalignment"].show()

    res = window["newgamedialog"].run()
    window["newgamedialog"].hide()
    if res != gtk.RESPONSE_OK: return
    
    widgid = gamewidget.addGameTab("")
    ccalign = gamewidget.getWidgets(widgid)[5]
    
    if window["useTimeCB"].get_active():
        ccalign.show()
        clock = window["ChessClock"]
        secs = window["spinbuttonH"].get_value()*3600
        secs += window["spinbuttonM"].get_value()*60
        secs += window["spinbuttonS"].get_value()
        gain = window["spinbuttonG"].get_value()
    else:
        ccalign.hide()
        clock = None
        secs = 0
        gain = 0
        
    for widget in ("whitePlayerCombobox", "blackPlayerCombobox", "whiteDifficulty", "blackDifficulty", "spinbuttonH", "spinbuttonM", "spinbuttonS", "spinbuttonG", "useTimeCB"):
        if hasattr(window[widget], "get_active"):
            v = window[widget].get_active()
        else: v = window[widget].get_value()
        myconf.set(widget, v)
    
    players = []
    for box, dfcbox, color in (("whitePlayerCombobox","whiteDifficulty",WHITE),
                              ("blackPlayerCombobox","blackDifficulty",BLACK)):
        choise = window[box].get_active()
        dfc = window[dfcbox].get_active()
        if choise != 0:
            engine = engines.availableEngines[choise-1][0]
            player = engine(engines.availableEngines[choise-1][1],color)
            player.connect("dead", engineDead, widgid)
            player.setStrength(dfc)
            if secs:
                player.setTime(secs, gain)
        else: player = Human(gamewidget.cur_widgets()[0], color)
        players += [player]
    
    gamewidget.setTabText(widgid, "%s vs %s" % (repr(players[0]), repr(players[1])))
    
    anaengines = [(e,a) for e,a in engines.availableEngines \
                                        if engines.getInfo((e,a))["canAnalyze"]]
    if len(anaengines) > 1:
        # We assume that the Pychess engine is the last
        engine, args = random.choice(anaengines[:-1])
    else: engine, args = anaengines[0]
    analyzer = engine(args, WHITE)
    analyzer.analyze()
    log.debug("Analyzer: %s\n" % repr(analyzer))

    game = Game(widgid, analyzer, players[0], players[1], clock, secs, gain)
    
    #game.connect("game_ended", GladeHandlers.__dict__["game_ended"])
    
    #TODO: enable this for tabs
    #window["properties1"].set_sensitive(True)
    return game, widgid

import thread
def engineDead (engine, widgid):
    gamewidget.setCurrent(widgid)
    gameList[widgid].kill()
    d = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
    d.set_markup(_("<big><b>Engine, %s, has died</b></big>") % repr(engine))
    d.format_secondary_text(_("PyChess has lost connection to the engine, probably because it has died.\n\nYou can try to start a new game with the engine, or try to play against another one."))
    d.connect("response", lambda d,r: d.hide())
    d.show_all()

def makeLogDialogReady ():
    System.LogDialog.add_destroy_notify(lambda: window["log_viewer1"].set_active(0))

def makeAboutDialogReady ():
    clb = window["aboutdialog1"].get_child().get_children()[1].get_children()[2]
    window["aboutdialog1"].set_version(VERSION)
    def callback(button, *args):
        window["aboutdialog1"].hide()
        return True
    clb.connect("activate", callback)
    clb.connect("clicked", callback)
    window["aboutdialog1"].connect("delete-event", callback)

def noOpenGame ():
    d = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
    d.set_markup(_("<big><b>No open game to save</b></big>"))
    d.format_secondary_text(_("You are not currently playing any game pychess can save for you."))
    d.connect("response", lambda d,r: d.hide())
    d.show_all()

class GladeHandlers:
    
    def on_ccalign_show (widget):
        clockHeight = window["ccalign"].get_allocation().height
        windowSize = window["window1"].get_size()
        window["window1"].resize(windowSize[0],windowSize[1]+clockHeight)
    
    def on_ccalign_hide (widget):
        clockHeight = window["ccalign"].get_allocation().height
        windowSize = window["window1"].get_size()
        window["window1"].resize(windowSize[0],windowSize[1]-clockHeight)
    
    #          Game Menu          #

    def on_new_game1_activate (widget):
        res = saveGameBefore(_("a new game starts"))
        if res == gtk.RESPONSE_CANCEL: return
        
        game, widgid = runNewGameDialog()
        if game:
            gameDic[widgid] = game
            game.run()

    def on_load_game1_activate (widget):
        res = saveGameBefore(_("you open a new game"))
        if res == gtk.RESPONSE_CANCEL: return
        
        res = opendialog.run()
        opendialog.hide()

        if res != gtk.RESPONSE_ACCEPT: return
        uri = opendialog.get_uri()
        filechooserbutton.set_uri(uri)
        game, widgid = runNewGameDialog(hideFC=False)
        
        if game:
            gameDic[widgid] = game
            game.load(filechooserbutton.get_uri()[7:])
            game.run()
    
    def on_save_game1_activate (widget):
        if not len(gameList):
            noOpenGame()
            return
        game = gameDic[gamewidget.cur_widgid()]
        if not game.isChanged:
            return
        if not game.lastSave[1]:
            return GladeHandlers.__dict__["on_save_game_as1_activate"](widget)
        else:
            GladeHandlers.__dict__["save"](lastSave[1])
        
    def on_save_game_as1_activate (widget):
        if not len(gameDic):
            noOpenGame()
            return
            
        #TODO: If file exists or has wrong filetype, the window is hidden..
        #      And the user has to reopen it to type a new name
        res = savedialog.run()
        savedialog.hide()
        if res != gtk.RESPONSE_ACCEPT: return False
        uri = savedialog.get_uri()[7:]
        
        s = uri.rfind(".")
        if s >= 0:
            ending = uri[s+1:]
        else: ending = None
        
        if savedialog.get_filter().filter((None,None,"foo",None)):
            if not ending in enddir:
                d = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
                folder, file = os.path.split(uri)
                d.set_markup(_("<big><b>Unknown filetype '%s'</b></big>") % ending)
                d.format_secondary_text(_("Wasn't able to save '%s' as pychess doesn't know the format '%s'.") % (uri,ending))
                d.run()
                d.hide()
                return
            saver = enddir[ending]
        else:
            for e,sr in enddir.iteritems():
                if savedialog.get_filter().filter((None,None,"."+e,None)):
                    if not ending in sr.__endings__:
                        uri += "." + e
                    break
                    
        if os.path.isfile(uri):
            d = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION)
            d.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, _("_Replace"), gtk.RESPONSE_ACCEPT)
            d.set_title(_("File exists"))
            folder, file = os.path.split(uri)
            d.set_markup(_("<big><b>A file named '%s' alredy exists. Would you like to replace it?</b></big>") % file)
            d.format_secondary_text(_("The file alredy exists in '%s'. If you replace it, its content will be overwritten.") % folder)
            res = d.run()
            d.hide()
            if res != gtk.RESPONSE_ACCEPT:
                return
        
        saver = enddir[ending]
        window.game.save(uri, saver)
    
    def save (uri):
        s = uri.rfind(".")
        if s >= 0:
            ending = uri[s+1:]
        else: return
        saver = enddir[ending]
        window.game.save(uri, saver)
    
    def on_properties1_activate (widget):
        #TODO Fix this in for the new Tab work
        window["event_entry"].set_text(window.game.event)
        window["site_entry"].set_text(window.game.site)
        window["round_spinbutton"].set_value(window.game.round)
        #TODO set the date
        window["game_info"].show()
        def hide_window(button, *args):
            window["game_info"].hide()
            return True
        def accept_new_properties(button, *args):
            game = gameDic[gamewidget.cur_widgid()]
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
    
    def on_quit1_activate (widget):
        res = saveGameBefore(_("exit"))
        if res == gtk.RESPONSE_CANCEL: return
        gtk.main_quit()
    
    #          View Menu          #
    
    def on_rotate_board1_activate (widget):
        gamewidget.cur_widgets()[0].view.fromWhite = \
            not gamewidgets.cur_widgets()[0].view.fromWhite
    
    def on_side_panel1_activate (widget):
        gamewidget.show_side_panel(widget.get_active())
    
    def on_show_cords_activate (widget):
        gamewidget.cur_widgets()[0].view.showCords = widget.get_active()
    
    def on_about1_activate (widget):
        window["aboutdialog1"].show()
    
    def on_log_viewer1_activate (widget):
        if widget.get_active():
            System.LogDialog.show()
        else: System.LogDialog.hide()
    
    def on_hint_mode_activate (widget):
        def on_analyze (analyzer, moves):
            gamewidget.cur_widgets()[0].view.greenarrow = moves[0].cords
        def on_clear (history):
            gamewidget.cur_widgets()[0].view.greenarrow = None
        def on_reset (history):
        	on_clear (history)
        	window["hint_mode"].set_active(False)
        if widget.get_active():
            try:
                if len(window.analyzer.analyzeMoves) >= 1:
                    gamewidget.cur_widgets()[0].view.greenarrow = \
                        window.analyzer.analyzeMoves[0].cords
                window.hintconid0 = window.analyzer.connect("analyze", on_analyze)
                history = gamewidget.cur_widgets()[0].view.history
                window.hintconid1 = history.connect("changed", on_clear)
                window.hintconid2 = history.connect("cleared", on_reset)
            except:
        	    window["hint_mode"].set_active(False)
        else:
            try:
                window.analyzer.disconnect(window.hintconid0)
                gamewidget.cur_widgets()[0].view.history.disconnect(window.hintconid1)
                gamewidget.cur_widgets()[0].view.history.disconnect(window.hintconid2)
            except: pass
            gamewidget.cur_widgets()[0].view.greenarrow = None
    
    def on_spy_mode_activate (widget):
        def on_analyze (analyzer, moves):
            if len(analyzer.analyzeMoves) >= 2:
                gamewidget.cur_widgets()[0].view.redarrow = moves[1].cords
        def on_clear (history):
            gamewidget.cur_widgets()[0].view.redarrow = None
        def on_reset (history):
        	on_clear (history)
        	window["spy_mode"].set_active(False)
        if widget.get_active():
            try:
                if len(window.analyzer.analyzeMoves) >= 2:
                    gamewidget.cur_widgets()[0].view.redarrow = \
                        window.analyzer.analyzeMoves[1].cords
                window.spyconid0 = window.analyzer.connect("analyze", on_analyze)
                history = gamewidget.cur_widgets()[0].view.history
                window.spyconid1 = history.connect("changed", on_clear)
                window.spyconid2 = history.connect("cleared", on_reset)
            except:
                window["spy_mode"].set_active(False)
        else:
            try:
                window.analyzer.disconnect(window.spyconid0)
                gamewidget.cur_widgets()[0].view.history.disconnect(window.spyconid1)
                gamewidget.cur_widgets()[0].view.history.disconnect(window.spyconid2)
            except: pass
            gamewidget.cur_widgets()[0].view.redarrow = None
    
    #          New Game Dialog          #

    def on_checkbutton4_clicked (widget):
        window["table6"].set_sensitive(widget.get_active())
    
    def on_whitePlayerCombobox_changed (widget):
        if widget.get_active() > 0:
            window["whiteDifficulty"].set_sensitive(True)
            window["whiteDifficulty"].set_active(1)
        else:
            window["whiteDifficulty"].set_sensitive(False)
            window["whiteDifficulty"].set_active(-1)
    
    def on_blackPlayerCombobox_changed (widget):
        if widget.get_active() > 0:
            window["blackDifficulty"].set_sensitive(True)
            window["blackDifficulty"].set_active(1)
        else:
            window["blackDifficulty"].set_sensitive(False)
            window["blackDifficulty"].set_active(-1)
    
    #          Action menu          #
    
    def on_call_flag_activate (widget):
        gamewidget.cur_widgets()[0].on_call_flag_activate (widget)

    def on_draw_activate (widget):
        gamewidget.cur_widgets()[0].on_draw_activate (widget)
        
    def on_resign_activate (widget):
        gamewidget.cur_widgets()[0].on_resign_activate (widget)

    def on_force_to_move_activate (widget):
        if window.game:
            window.game.activePlayer.hurry()
    
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
        myconf.set("show_tip_at_startup", True)
        TipOfTheDay.TipOfTheDay()
    
    #          Other          #
    
    def on_notebook2_switch_page (widget, page, page_num):
        window["notebook3"].set_current_page(page_num)

class PyChess:
    def __init__(self):
        self.initGlade()
    
    def initGlade(self):
        global window
        window = self
    
        os.chdir(os.path.abspath(os.path.dirname(__file__)))
        gtk.glade.set_custom_handler(self.widgetHandler)
        self.widgets = gtk.glade.XML("glade/PyChess.glade")
        
        self["window1"].connect("destroy", gtk.main_quit)
        self.widgets.signal_autoconnect(GladeHandlers.__dict__)
        
        self["window1"].show_all()
        
        #Very ugly hack, needed because of pygtk bug 357022
        #http://bugzilla.gnome.org/show_bug.cgi?id=357022
        from widgets.BookCellRenderer import BookCellRenderer
        self.BookCellRenderer = BookCellRenderer
        
        self.game = None
        #makeSidePanelReady()
        makeFileDialogReady()
        makeLogDialogReady()
        makeAboutDialogReady()
        
        gamewidget.set_widgets(self)
        #gamewidget.addGameTab("Thomas vs. others")
        #gamewidget.setTabReady(0, True)
        #gamewidget.addGameTab("Thomas vs. others2")
        
        win = self["window1"]
        def do ():
            r = win.get_allocation()
            w, h = r.width, r.height
            myconf.set("window_width", w)
            myconf.set("window_height", h)
        atexit.register(do)
        w = myconf.get("window_width")
        h = myconf.get("window_height")
        if w and h:
            self["window1"].resize(w,h)
        TipOfTheDay.TipOfTheDay()
        
        
    def __getitem__(self, key):
        return self.widgets.get_widget(key)
    
    from UserDict import UserDict
    class Files (UserDict):
        def __getitem__(self, folder="./"):
            folder = os.path.abspath(folder)
            if not folder in self:
                files = os.listdir(folder)
                files = [f[:-3] for f in files if f[-3:] == ".py"]
                self[folder] = files
            return self.data[folder]
    files = Files()
    
    def widgetHandler (self, glade, functionName, widgetName, str1, str2, int1, int2):
        if widgetName in self.files["widgets"]:
            module = __import__("widgets/"+widgetName, globals(), locals())
            return getattr(module,widgetName)()
        else:
            log.error("Uncaught widget %s %s, %s %s %d %d" % \
                    (functionName, widgetName, str1, str1, int1, int2))

if __name__ == "__main__":
    PyChess()
    import signal
    signal.signal(signal.SIGINT, gtk.main_quit)
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    gtk.gdk.threads_init()
    gtk.main()

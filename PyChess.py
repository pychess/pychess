#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import pygtk
pygtk.require("2.0")
import sys, gtk, gtk.glade, os
import pango

import gettext
gettext.install("pychess",localedir="lang",unicode=1)
gtk.glade.bindtextdomain("pychess","lang")
gtk.glade.textdomain("pychess")

from System.Log import log

from Players import *
from Players.Human import Human
from System import myconf
import thread
from Game import game
import Game
from Utils.Oracle import Oracle

def saveGameBefore (action):
    #TODO: Test om noget er ændret!
    defText = window["savedialogtext1"].get_label()
    window["savedialogtext1"].set_markup(defText % action)
    response = window["savegamedialog"].run()
    window["savegamedialog"].hide()
    window["savedialogtext1"].set_markup(defText)
    if response == gtk.RESPONSE_YES: window["save_game1"].activate()
    return response

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

def makeNewGameDialogReady ():
    it = gtk.icon_theme_get_default()

    items = []
    for level, stock in ((_("Beginner"), "stock_weather-few-clouds"), 
                         (_("Intermediate"), "stock_weather-cloudy"),
                         (_("Expert"), "stock_weather-storm")):
        image = it.load_icon(stock, 16, gtk.ICON_LOOKUP_USE_BUILTIN)
        items += [(image, level)]

    for combo in (window["combobox7"], window["combobox8"]):
        createCombo(combo, items)

    image = it.load_icon("stock_people", 24, gtk.ICON_LOOKUP_USE_BUILTIN)
    items = [(image, _("Human Being"))]
    image = it.load_icon("stock_notebook", 24, gtk.ICON_LOOKUP_USE_BUILTIN)
    
    for engine in [str(e).split(".")[-1] for e in window.engines]:
        items += [(image, engine)]
    for combo in (window["combobox5"], window["combobox6"]):
        createCombo(combo, items)
        
    window["combobox5"].set_active(0)
    window["combobox6"].set_active(min(1,len(window.engines)))
    GladeHandlers.__dict__['on_combobox6_changed'](window["combobox6"])
    
    for widget in ("combobox5", "combobox6", "combobox7", "combobox8",
            "spinbuttonH", "spinbuttonM", "spinbuttonS", "spinbuttonG", "useTimeCB"):
        v = myconf.get(widget)
        if v != None:
            if hasattr(window[widget], "set_active"):
                window[widget].set_active(v)
            else: window[widget].set_value(v)
        
def on_sidepanel_change (client, *args):
    if myconf.get("sidepanel"):
        window["sidepanel"].show()
        if window["sidepanel"].get_allocation().width > 1:
            panelWidth = window["sidepanel"].get_allocation().width
        else: panelWidth = window["panelbook"].get_size_request()[0] +10
        windowSize = window["window1"].get_size()
        window["window1"].resize(windowSize[0]+panelWidth,windowSize[1])
    else:
        panelWidth = window["sidepanel"].get_allocation().width
        window["sidepanel"].hide()
        windowSize = window["window1"].get_size()
        window["window1"].resize(windowSize[0]-panelWidth,windowSize[1])
    window["side_panel1"].set_active(myconf.get("sidepanel"))

def makeSidePanelReady ():
    start = 0 #Todo: must be controlled by gconf
    
    panels = ["sidepanel/"+f for f in os.listdir("sidepanel")]
    panels = [f[:-3] for f in panels if f.endswith(".py")]
    for panel in [__import__(f, locals()) for f in panels]:
        panel.ready(window)
        window["ToggleComboBox"].addItem(panel.__title__)
        num = window["panelbook"].append_page(panel.__widget__)
        panel.__widget__.show()
        if hasattr(panel, "__active__") and panel.__active__:
            start = num
    
    window["ToggleComboBox"].connect("changed", 
            lambda w,i: window["panelbook"].set_current_page(i))
            
    window["panelbook"].set_current_page(start)
    window["ToggleComboBox"].active = start
    
    on_sidepanel_change(None)
    myconf.notify_add ("sidepanel", on_sidepanel_change)
    
class GladeHandlers:
    
    #          Game Menu          #
    
    def on_new_game1_activate (widget):
        #res = saveGameBefore(_("a new game starts"))
        #if res == gtk.RESPONSE_CANCEL: return
        
        res = window["newgamedialog"].run()
        window["newgamedialog"].hide()
        if res == gtk.RESPONSE_CANCEL: return
        
        if window["useTimeCB"].get_active():
            window["ccalign"].show()
            clock = window["ChessClock"]
            secs = window["spinbuttonH"].get_value()*3600
            secs += window["spinbuttonM"].get_value()*60
            secs += window["spinbuttonS"].get_value()
            gain = window["spinbuttonG"].get_value()
        else:
            window["ccalign"].hide()
            clock = None
            secs = 0
            gain = 0
        
        for widget in ("combobox5", "combobox6", "combobox7", "combobox8",
                "spinbuttonH", "spinbuttonM", "spinbuttonS", "spinbuttonG", "useTimeCB"):
            if hasattr(window[widget], "get_active"):
                v = window[widget].get_active()
            else: v = window[widget].get_value()
            myconf.set(widget, v)
        
        players = []
        for box, dfcbox, pnum in (("combobox5","combobox7",0),
                                  ("combobox6","combobox8",1)):
            choise = window[box].get_active()
            dfc = window[dfcbox].get_active()
            if choise != 0:
                player = window.engines[choise-1]()
                player.setStrength(dfc)
                if secs:
                    player.setTime(secs, gain)
            else: player = Human(window["BoardControl"], pnum)
            players += [player]
        
        if id in window.sbids:
            window["statusbar1"].pop(id)
        window["BoardControl"].view.shown = 0
        window["ChessClock"].stop()
        Game.kill()
        t = thread.start_new(game, (window["BoardControl"].view.history, window.oracle, players[0], players[1], clock, secs, gain))
    
    def on_ccalign_show (widget):
        clockHeight = window["ccalign"].get_allocation().height
        windowSize = window["window1"].get_size()
        window["window1"].resize(windowSize[0],windowSize[1]+clockHeight)
    
    def on_ccalign_hide (widget):
        clockHeight = window["ccalign"].get_allocation().height
        windowSize = window["window1"].get_size()
        window["window1"].resize(windowSize[0],windowSize[1]-clockHeight)
    
    def on_load_game1_activate (widget):
        #res = saveGameBefore(_("you open a new game"))
        #if res == gtk.RESPONSE_CANCEL: return
        pass #TODO
    
    def on_save_game1_activate (widget):
        pass #TODO
    
    def on_save_game_as1_activate (widget):
        pass #TODO
    
    def on_quit1_activate (widget):
        #res = saveGameBefore(_("exit"))
        #if res == gtk.RESPONSE_CANCEL: return
        gtk.main_quit()
    
    #          View Menu          #
    
    def on_rotate_board1_activate (widget):
        window["BoardControl"].view.fromWhite = not window["BoardControl"].view.fromWhite
    
    def on_side_panel1_activate (widget):
        myconf.set("sidepanel", widget.get_active())
    
    def on_sidepanel_closebutton_clicked (widget):
        myconf.set("sidepanel",False)
    
    def on_book1_activate (widget):
        pass
    
    def on_hint1_activate (widget):
        pass #TODO
    
    def on_about1_activate (widget):
        window["aboutdialog1"].show()
    
    def on_hint_mode_activate (widget):
        def foretold_move (oracle, move, score):
            if len(oracle.future) == 1:
                window["BoardControl"].view.greenarrow = move.cords
        def rmfirst (oracle):
            if len(oracle.future) >= 1:
                window["BoardControl"].view.greenarrow = oracle.future[0][0].cords
        def cleared (oracle):
            window["BoardControl"].view.greenarrow = None
        if widget.get_active():
            if len(window.oracle.future) >= 1:
                window["BoardControl"].view.greenarrow = window.oracle.future[0][0].cords
            window.hintconid0 = window.oracle.connect("foretold_move", foretold_move)
            window.hintconid1 = window.oracle.connect("rmfirst", rmfirst)
            window.hintconid2 = window.oracle.connect("clear", cleared)
        else:
            window.oracle.disconnect(window.hintconid0)
            window.oracle.disconnect(window.hintconid1)
            window.oracle.disconnect(window.hintconid2)
            window["BoardControl"].view.greenarrow = None
    
    def on_spy_mode_activate (widget):
        #Case: Spy slås til efter trækket er i gang
        def foretold_move (oracle, move, score):
            if len(oracle.future) == 2:
                window["BoardControl"].view.redarrow = move.cords
        def rmfirst (oracle):
            if len(oracle.future) >= 2:
                window["BoardControl"].view.redarrow = oracle.future[1][0].cords
        def cleared (oracle):
            window["BoardControl"].view.redarrow = None
        if widget.get_active():
            if len(window.oracle.future) >= 2:
                window["BoardControl"].view.redarrow = window.oracle.future[1][0].cords
            window.spyconid0 = window.oracle.connect("foretold_move", foretold_move)
            window.spyconid1 = window.oracle.connect("rmfirst", rmfirst)
            window.spyconid2 = window.oracle.connect("clear", cleared)
        else:
            window.oracle.disconnect(window.spyconid0)
            window.oracle.disconnect(window.spyconid1)
            window.oracle.disconnect(window.spyconid2)
            window["BoardControl"].view.redarrow = None
    
    #          New Game Dialog          #

    def on_checkbutton4_clicked (widget):
        window["table6"].set_sensitive(widget.get_active())
    
    def on_combobox5_changed (widget):
        if widget.get_active() != 0:
            window["combobox7"].set_sensitive(True)
            window["combobox7"].set_active(1)
        else:
            window["combobox7"].set_sensitive(False)
            window["combobox7"].set_active(-1)
    
    def on_combobox6_changed (widget):
        if widget.get_active() != 0:
            window["combobox8"].set_sensitive(True)
            window["combobox8"].set_active(1)
        else:
            window["combobox8"].set_sensitive(False)
            window["combobox8"].set_active(-1)
    
    #          Cairo Board          #
    
    def on_start_clicked (widget):
        window["BoardControl"].view.shown = 0
    
    def on_backward_clicked (widget):
        window["BoardControl"].view.shown -= 1
    
    def on_forward_clicked (widget):
        window["BoardControl"].view.shown += 1
    
    def on_end_clicked (widget):
        if window["BoardControl"].view.history:
            window["BoardControl"].view.shown = len(window["BoardControl"].view.history)-1

from time import time

class PyChess:
    def __init__(self):
        self.initGlade()
    
    def initGlade(self):
        global window
        window = self
    
        os.chdir(os.path.abspath(os.path.dirname(__file__)))
        gtk.glade.set_custom_handler(self.widgetHandler)
        self.widgets = gtk.glade.XML("glade/PyChess.glade")
        
        self["ChessClock"].connect("time_out",
            lambda w,p: self.end("Player %d is timeout" % p))
        self["BoardControl"].view.history.connect("game_ended",
            lambda w,r: self.end(r == 2 and "Mate" or "Stale"))
        
        self["window1"].connect("destroy", gtk.main_quit)
        self.widgets.signal_autoconnect(GladeHandlers.__dict__)
        
        self["BoardControl"].eventbox = self["eventbox1"]
        
        self["window1"].show_all()
        
        self.oracle = Oracle()
        self.oracle.attach(self["BoardControl"].view.history)
        
        self.loadEngines()
        makeNewGameDialogReady()
        
        #Very ugly hack, needed because of pygtk bug 357022
        #http://bugzilla.gnome.org/show_bug.cgi?id=357022
        from BookCellRenderer import BookCellRenderer
        self.BookCellRenderer = BookCellRenderer
        
        makeSidePanelReady()
        
    def __getitem__(self, key):
        return self.widgets.get_widget(key)
    
    sbids = [0]
    def end (self, message):
        self["statusbar1"].push(self.sbids[-1], message)
        self.sbids.append(self.sbids[-1]+1)
    
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
    
    engines = []
    def loadEngines (self):
        from Players.Engine import Engine
        from types import ClassType
        for name, module in globals().iteritems():
            for attr in [getattr(module, a) for a in dir(module)]:
                if type(attr) is ClassType and issubclass(attr, Engine) and attr != Engine:
                    if module.testEngine():
                        self.engines += [attr]
    
    def widgetHandler (self, glade, functionName, widgetName, str1, str2, int1, int2):
        if widgetName in self.files["."]:
            module = __import__(widgetName, globals(), locals())
            return getattr(module,widgetName)()
        else:
            log.error("Uncaught widget %s %s, %s %s %d %d" % \
                    (functionName, widgetName, str1, str1, int1, int2))

if __name__ == "__main__":
    PyChess()
    gtk.gdk.threads_init()
    gtk.main()

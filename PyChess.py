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

from Utils.Log import log

from Players import *
from Players.Human import Human
import myconf
import thread
from Game import game

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

def makePromotionDialogReady ():
    window["promotionDialog"].hide()

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
                   "spinbuttonH", "spinbuttonM", "spinbuttonS", "spinbuttonG"):
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
    for panel in [__import__(f, globals()) for f in panels]:
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
        
        #window["ChessClock"].reset()
        #window["CairoBoard"].reset()
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
                       "spinbuttonH", "spinbuttonM", "spinbuttonS", "spinbuttonG"):
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
                player.setTime(secs, gain)
            else: player = Human(window["CairoBoard"], pnum)
            players += [player]
        
        thread.start_new(game, (window["CairoBoard"], players[0], players[1], clock, secs, gain))
        
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
        window["CairoBoard"].fromWhite = not window["CairoBoard"].fromWhite
    
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
    
    def on_eventbox1_button_press_event (widget, event):
        window["CairoBoard"].button_press(widget, event)
    
    def on_eventbox1_button_release_event (widget, event):
        window["CairoBoard"].button_release(widget, event)
    
    def on_eventbox1_focus_out_event (widget, event):
        window["CairoBoard"].focus_out(widget, event)
    
    def on_eventbox1_motion_notify_event (widget, event):
        window["CairoBoard"].motion_notify(widget, event)
    
    def on_eventbox1_leave_notify_event (widget, event):
        window["CairoBoard"].leave_notify(widget, event)


    def on_start_clicked (widget):
        window["CairoBoard"].shown = 0
    
    def on_backward_clicked (widget):
        window["CairoBoard"].shown -= 1
    
    def on_forward_clicked (widget):
        window["CairoBoard"].shown += 1
    
    def on_end_clicked (widget):
        if window["CairoBoard"].history:
            window["CairoBoard"].shown = len(window["CairoBoard"].history)-1

class PyChess:
    def __init__(self):
        self.initGlade()
    
    def initGlade(self):
        global window
        window = self
    
        os.chdir(os.path.abspath(os.path.dirname(__file__)))
        gtk.glade.set_custom_handler(self.widgetHandler)
        self.widgets = gtk.glade.XML("glade/PyChess.glade")
        
        self["ChessClock"].connect("time_out", self.time_out)
        self["window1"].connect("destroy", gtk.main_quit)
        self.widgets.signal_autoconnect(GladeHandlers.__dict__)
        
        self["CairoBoard"].eventbox = self["eventbox1"]
        
        self["window1"].show_all()
        
        self.loadEngines()
        makeNewGameDialogReady()
        makeSidePanelReady()
        makePromotionDialogReady()
        
    def __getitem__(self, key):
        return self.widgets.get_widget(key)
    
    def time_out (self, widget, player):
        m = "Player %d is timeout" % player
        from time import time
        self["statusbar1"].push(int(time()), m)
    
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
                if type(attr) is ClassType and \
                        issubclass(attr, Engine) and \
                        attr != Engine:
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

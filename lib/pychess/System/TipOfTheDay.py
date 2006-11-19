import pygtk
pygtk.require("2.0")
import sys, gtk, gtk.glade, os
import pango, gobject
import myconf
from pychess.Utils.const import prefix

class TipOfTheDay:
    def __init__(self):
        self.dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_INFO, gtk.BUTTONS_NONE, None)
        self.dlg.set_icon_from_file(prefix("glade/pychess24.png"))
        self.dlg.set_title("Tip of the Day")
        self.dlg.set_markup(self.get_a_random_tip())
        self.dlg.add_button("Don't show anymore", 83)
        self.dlg.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
        self.dlg.set_resizable( False)
        # print self.get_show_tip_at_startup()
        if  not self.get_show_tip_at_startup():
            return
        ret = self.dlg.run()
        if ret == 83:
            self.set_show_tip_at_startup(False)
        self.dlg.hide()
        self.dlg.destroy()
        return
        
    def get_a_random_tip(self):
        #TODO Return a random tip
        return "You can start a new game by pressing \n <b>Game -> New Game</b>"
        pass
    
    def set_show_tip_at_startup(self, value):
        myconf.set("show_tip_at_startup", value)
        pass
    
    def get_show_tip_at_startup(self):
        if myconf.get("show_tip_at_startup") == None:
            return True
        return myconf.get("show_tip_at_startup")

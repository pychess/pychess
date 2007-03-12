import gtk, gobject, sys

from pychess.System import myconf
from pychess.System import gstreamer
from pychess.Utils.const import *

import telnet
from telnet import LogOnError
import thread
import icLounge

firstRun = True
def run():
    
    if telnet.client:
        icLounge.show()
        return
    
    global firstRun
    if firstRun:
        initialize()
        firstRun = False
        
        def callback (client, signal):
            if signal == IC_CONNECTED:
                widgets["fics_logon"].hide()
                icLounge.show()
        telnet.connectStatus(callback)
    
    response = widgets["fics_logon"].run()
    if response != gtk.RESPONSE_OK:
        widgets["fics_logon"].hide()
    else:
        
        if widgets["logOnAsGuest"].get_active():
            username = "guest"
            password = ""
        else:
            username = widgets["nameEntry"].get_text()
            password = widgets["passEntry"].get_text()
        
        widgets["progressbar"].show()
        widgets["mainvbox"].set_sensitive(False)
        widgets["connectButton"].set_sensitive(False)
        def callback ():
            widgets["progressbar"].pulse()
            if telnet.connected:
                widgets["progressbar"].hide()
                widgets["mainvbox"].set_sensitive(True)
                widgets["connectButton"].set_sensitive(True)
                return False
            return True
        gobject.timeout_add(30, callback)
        
        def func ():
            def error (title, text):
                
                d = gtk.MessageDialog(
                    type = gtk.MESSAGE_ERROR, buttons = gtk.BUTTONS_OK)
                d.set_markup("<big><b>%s</b></big>" % _(title))
                d.format_secondary_text(str(e))
                def callback (button):
                    d.hide()
                    widgets["mainvbox"].set_sensitive(True)
                    widgets["connectButton"].set_sensitive(True)
                    run()
                b = d.get_children()[0].get_children()[-1].get_children()[0]
                b.connect("clicked", callback)
                widgets["progressbar"].hide()
                d.show()
            try:
                telnet.connect ("freechess.org", 5000, username, password)
            except IOError, e:
                gobject.idle_add(error, _("Connection Error"), str(e))
            except LogOnError, e:
                gobject.idle_add(error, _("Log on Error"), str(e))
        thread.start_new(func, ())

def initialize():
    
    global widgets
    class Widgets:
        def __init__ (self, glades):
            self.widgets = glades
        def __getitem__(self, key):
            return self.widgets.get_widget(key)
    widgets = Widgets(gtk.glade.XML(prefix("glade/fics_logon.glade")))
    
    def on_logOnAsGuest_toggled (check):
        widgets["logOnTable"].set_sensitive(not check.get_active())
    widgets["logOnAsGuest"].connect("toggled", on_logOnAsGuest_toggled)
    
    ############################################################################
    # Easy initing                                                             #
    ############################################################################
    
    methodDict = {
        gtk.CheckButton: ("get_active", "set_active", "toggled"),
        gtk.Entry: ("get_text", "set_text", "changed"),
        gtk.ComboBox: ("get_active", "set_active", "changed")
    }
    
    easyWidgets = [
        "logOnAsGuest"
    ]
    
    class ConnectionKeeper:
        def __init__ (self, key):
            
            if type(key) in (tuple, list):
                self.key, get_value, set_value = key
                self.widget = widget = widgets[self.key]
                self.get_value = lambda: get_value(self.widget)
                self.set_value = lambda v: set_value(self.widget, v)
            else:
                self.key = key
                self.widget = widget = widgets[self.key]
                self.get_value = getattr(widget, methodDict[type(widget)][0])
                self.set_value = getattr(widget, methodDict[type(widget)][1])
            
            self.signal = methodDict[type(widget)][2]
            
            self.set_value(myconf.get(self.key))
            widget.connect(self.signal,
                lambda *args: myconf.set(self.key, self.get_value()))
            myconf.notify_add(self.key,
                lambda *args: self.set_value(myconf.get(self.key)))
    
    for key in easyWidgets:
        ConnectionKeeper(key)

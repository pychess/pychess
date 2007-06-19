from socket import SHUT_RDWR
import webbrowser

import gtk, gobject, sys

from pychess.System.ThreadPool import pool
from pychess.System import myconf, gstreamer, uistuff
from pychess.Utils.const import *
import telnet, icLounge

firstRun = True
def run():
    
    if telnet.connected:
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
    
    widgets["fics_logon"].show()

pulser = None
def on_connectButton_clicked (button):
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
            widgets["messagePanel"].hide()
            return False
        return True
    
    global pulser
    pulser = gobject.timeout_add(30, callback)
    
    pool.start(doConnect, username, password)

def doConnect (username, password):
    def error (title, text):
        widgets["mainvbox"].set_sensitive(True)
        widgets["connectButton"].set_sensitive(True)
        widgets["progressbar"].hide()
        
        widgets["messageTitle"].set_markup("<b>%s</b>" % title)
        widgets["messageText"].set_text(str(e))
        widgets["messagePanel"].show_all()
        
        global pulser
        if pulser != None:
            gobject.source_remove(pulser)
            pulser = None
    try:
        telnet.connect ("freechess.org", 5000, username, password)
    except IOError, e:
        telnet.client = None
        gobject.idle_add(error, _("Connection Error"), str(e))
    except telnet.LogOnError, e:
        telnet.client = None
        gobject.idle_add(error, _("Log on Error"), str(e))
    except telnet.InterruptError, e:
        telnet.client = None
        gobject.idle_add(error, _("Connection was broken"), str(e))
    except EOFError, e:
        telnet.client = None
        gobject.idle_add(error, _("Connection was closed"), str(e))

def cancel ():
    if telnet.client:
        telnet.client.interrupt()
        widgets["mainvbox"].set_sensitive(True)
        widgets["connectButton"].set_sensitive(True)
    widgets["fics_logon"].hide()
    return True

firstDraw = True

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
    uistuff.keep(widgets["logOnAsGuest"], "logOnAsGuest")
    
    widgets["cancelButton"].connect("clicked", lambda b: cancel())
    widgets["fics_logon"].connect("delete-event", lambda w, e: cancel(True))
    widgets["createNewButton"].connect("clicked",
        lambda *a: webbrowser.open("http://freechess.org/Register/index.html"))
    widgets["connectButton"].connect("clicked", on_connectButton_clicked)
    
    # Init yellow error box
    
    uistuff.makeYellow(widgets["messagePanel"])

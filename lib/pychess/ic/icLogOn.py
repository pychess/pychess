import gtk, gobject, sys

from pychess.System import myconf
from pychess.System import gstreamer
from pychess.Utils.const import *

import telnet
from telnet import LogOnError, InterruptError
import thread
import icLounge
from socket import SHUT_RDWR

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
    
    thread.start_new(doConnect, (username, password))

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
    except LogOnError, e:
        telnet.client = None
        gobject.idle_add(error, _("Log on Error"), str(e))
    except InterruptError, e:
        telnet.client = None
        gobject.idle_add(error, _("Connection was broken"), str(e))
    except EOFError, e:
        telnet.client = None
        gobject.idle_add(error, _("Connection was closed"), str(e))

def cancel (hide=False):
    if telnet.client:
        telnet.client.interrupt()
        widgets["mainvbox"].set_sensitive(True)
        widgets["connectButton"].set_sensitive(True)
        if hide:
            widgets["fics_logon"].hide()
            return True
    else:
        widgets["fics_logon"].hide()
        if hide:
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
    
    widgets["cancelButton"].connect("clicked", lambda b: cancel())
    widgets["fics_logon"].connect("delete-event", lambda w, e: cancel(True))
    
    widgets["connectButton"].connect("clicked", on_connectButton_clicked)
    
    tooltip = gtk.Tooltips()
    tooltip.force_window()
    tooltip.tip_window.ensure_style()
    tooltipStyle = tooltip.tip_window.get_style()
    widgets["messagePanel"].set_style(tooltipStyle)
    
    def on_messagePanel_expose_event (widget, event):
        allocation = widget.allocation
        widget.style.paint_flat_box (widget.window,
            gtk.STATE_NORMAL, gtk.SHADOW_NONE, None, widget, "tooltip",
            allocation.x, allocation.y, allocation.width, allocation.height )
        global firstDraw
        if firstDraw:
            firstDraw = False
            widget.queue_draw()
    widgets["messagePanel"].connect("expose-event", on_messagePanel_expose_event)
    
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

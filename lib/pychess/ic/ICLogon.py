import socket
from socket import SHUT_RDWR
import webbrowser
import re

import gtk, gobject, sys

from pychess.System.repeat import repeat_sleep
from pychess.System.ThreadPool import pool
from pychess.System import gstreamer, uistuff, glock
from pychess.System.prefix import addDataPrefix
from pychess.System import uistuff
from pychess.Utils.const import *

from FICSConnection import FICSConnection, LogOnError
from ICLounge import ICLounge

dialog = None
def run():
    global dialog
    
    if not dialog:
        dialog = ICLogon()
    
    if dialog.lounge:
        dialog.lounge.show()
    else:
        dialog.show()

class ICLogon:
    def __init__ (self):
        self.widgets = uistuff.GladeWidgets("fics_logon.glade")
        uistuff.keepWindowSize("fics_logon", self.widgets["fics_logon"],
                               defaultPosition=uistuff.POSITION_GOLDEN)
        
        self.widgets["fics_logon"].connect('key-press-event',
                lambda w, e: e.keyval == gtk.keysyms.Escape and w.hide())
        
        
        def on_logOnAsGuest_toggled (check):
            self.widgets["nameLabel"].set_sensitive(not check.get_active())
            self.widgets["nameEntry"].set_sensitive(not check.get_active())
            self.widgets["passwordLabel"].set_sensitive(not check.get_active())
            self.widgets["passEntry"].set_sensitive(not check.get_active())
        self.widgets["logOnAsGuest"].connect("toggled", on_logOnAsGuest_toggled)
        uistuff.keep(self.widgets["logOnAsGuest"], "logOnAsGuest")
        
        uistuff.makeYellow(self.widgets["messagePanel"])
        
        self.widgets["cancelButton"].connect("clicked", self.onCancel, True)
        self.widgets["stopButton"].connect("clicked", self.onCancel, False)
        self.widgets["fics_logon"].connect("delete-event", self.onClose)
        
        self.widgets["createNewButton"].connect("clicked", self.onCreateNew)
        self.widgets["connectButton"].connect("clicked", self.onConnectClicked)
        
        self.connection = None
        self.lounge = None
    
    def show (self):
        self.widgets["fics_logon"].show()
    
    def hide (self):
        self.widgets["fics_logon"].hide()
    
    def showConnecting (self):
        self.widgets["progressbarBox"].show()
        self.widgets["mainbox"].set_sensitive(False)
        self.widgets["connectButton"].hide()
        self.widgets["stopButton"].show()
        
        def pulse ():
            self.widgets["progressbar"].pulse()
            return not self.connection.isConnected()
        self.pulser = gobject.timeout_add(30, pulse)
    
    def showNormal (self):
        self.widgets["mainbox"].set_sensitive(True)
        self.widgets["connectButton"].show()
        self.widgets["fics_logon"].set_default(self.widgets["connectButton"])
        self.widgets["stopButton"].hide()
        self.widgets["progressbarBox"].hide()
        self.widgets["progressbar"].set_text("")
        gobject.source_remove(self.pulser)
    
    def showMessage (self, connection, message):
        self.widgets["progressbar"].set_text(message)
    
    def onCancel (self, widget, hide):
        if self.connection and self.connection.isConnecting():
            self.connection.disconnect()
            self.connection = None
            self.showNormal()
        if hide:
            self.widgets["fics_logon"].hide()
        return True
    
    def onClose (self, widget, event):
        self.onCancel(widget, True)
        return True
    
    def onCreateNew (self, button):
        webbrowser.open("http://freechess.org/Register/index.html")
    
    def showError (self, connection, error):
        # Don't bring up errors, if we have pressed "stop"
        if self.connection != connection:
            return True
        
        text = str(error)
        if isinstance (error, IOError):
            title = _("Connection Error")
        elif isinstance (error, LogOnError):
            title =_("Log on Error")
        elif isinstance (error, EOFError):
            title = _("Connection was closed")
        elif isinstance (error, socket.error):
            title = _("Connection Error")
            text = ", ".join(map(str,error.args))
        elif isinstance (error, socket.gaierror) or \
                isinstance (error, socket.herror):
            title = _("Address Error")
            text = ", ".join(map(str,error.args))
        else:
            title = str(error.__class__)
        
        self.showNormal()
        
        pars = str(text).split("\n")
        textsVbox = self.widgets["textsVbox"]
        
        while len(textsVbox.get_children()) > len(pars)+1:
            child = textsVbox.get_children()[-1]
            textsVbox.remove(child)
        
        while len(textsVbox.get_children()) < len(pars)+1:
            label = gtk.Label()
            label.props.wrap = True
            label.props.xalign = 0
            label.props.justify = gtk.JUSTIFY_LEFT
            textsVbox.add(label)
        
        textsVbox.get_children()[0].set_markup("<b><big>%s</big></b>" % title)
        for i, par in enumerate(pars):
            textsVbox.get_children()[i+1].set_text(par)
        
        self.widgets["messagePanel"].show_all()
    
    def onConnected (self, connection):
        self.lounge = ICLounge(connection)
        self.hide()
        self.lounge.show()
        
        self.showNormal()
        self.widgets["messagePanel"].hide()
    
    def onDisconnected (self, connection):
        global dialog
        dialog = None
    
    def onConnectClicked (self, button):
        if self.widgets["logOnAsGuest"].get_active():
            username = "guest"
            password = ""
        else:
            username = self.widgets["nameEntry"].get_text()
            password = self.widgets["passEntry"].get_text()
        
        ports = self.widgets["portsEntry"].get_text()
        ports = map(int, re.findall("\d+", ports))
        if not 23 in ports: ports.append(23)
        if not 5000 in ports: ports.append(5000)
        self.showConnecting()
        
        self.connection = FICSConnection("freechess.org", ports, username, password)
        self.connection.connect("connected", self.onConnected)
        self.connection.connect("disconnected", self.onDisconnected)
        self.connection.connect("error", self.showError)
        self.connection.connect("connectingMsg", self.showMessage)
        
        self.connection.start()

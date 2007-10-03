import socket
from socket import SHUT_RDWR
import webbrowser

import gtk, gobject, sys

from pychess.System.repeat import repeat_sleep
from pychess.System.ThreadPool import pool
from pychess.System import gstreamer, uistuff, glock
from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import *

from VerboseTelnet import VerboseTelnet, InterruptError
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
        
        def on_logOnAsGuest_toggled (check):
            self.widgets["logOnTable"].set_sensitive(not check.get_active())
        self.widgets["logOnAsGuest"].connect("toggled", on_logOnAsGuest_toggled)
        uistuff.keep(self.widgets["logOnAsGuest"], "logOnAsGuest")
        
        uistuff.makeYellow(self.widgets["messagePanel"])
        
        self.widgets["cancelButton"].connect("clicked", self.onCancel, False)
        self.widgets["fics_logon"].connect("delete-event", self.onClose)
        self.widgets["createNewButton"].connect("clicked", self.onCreateNew)
        self.widgets["connectButton"].connect("clicked", self.onConnectClicked)
        
        self.connection = None
        self.lounge = None
    
    def show (self):
        self.widgets["fics_logon"].show()
    
    def hide (self):
        self.widgets["fics_logon"].hide()
    
    def onCancel (self, widget, hide):
        if self.connection and self.connection.isConnecting():
            self.connection.disconnect()
            self.connection = None
            self.widgets["mainvbox"].set_sensitive(True)
            self.widgets["connectButton"].set_sensitive(True)
            self.widgets["progressbar"].hide()
            gobject.source_remove(self.pulser)
        if hide:
            self.widgets["fics_logon"].hide()
        return True
    
    def onClose (self, widget, event):
        self.onCancel(widget, True)
        return True
    
    def onCreateNew (self, button):
        webbrowser.open("http://freechess.org/Register/index.html")
    
    def showError (self, connection, error):
        text = str(error)
        if isinstance (error, IOError):
            title = _("Connection Error")
        elif isinstance (error, LogOnError):
            title =_("Log on Error")
        elif isinstance (error, InterruptError):
            title = _("Connection was broken")
        elif isinstance (error, EOFError):
            title = _("Connection was closed")
        elif isinstance (error, socket.error):
            title = _("Connection Error")
            text = ", ".join(map(str,error.args))
        elif isinstance (error, socket.gaierror) or \
                isinstance (error, socket.herror):
            title = _("Adress Error")
            text = ", ".join(map(str,error.args))
        else:
            title = str(error.__class__)
        
        self.widgets["mainvbox"].set_sensitive(True)
        self.widgets["connectButton"].set_sensitive(True)
        self.widgets["progressbar"].hide()
        
        self.widgets["messageTitle"].set_markup("<b>%s</b>" % title)
        self.widgets["messageText"].set_text(str(text))
        self.widgets["messagePanel"].show_all()
    
    def onConnected (self, connection):
        self.widgets["progressbar"].hide()
        self.widgets["mainvbox"].set_sensitive(True)
        self.widgets["connectButton"].set_sensitive(True)
        self.widgets["messagePanel"].hide()
        
        self.lounge = ICLounge(connection)
        self.lounge.show()
        self.hide()
    
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
        
        self.widgets["progressbar"].show()
        self.widgets["mainvbox"].set_sensitive(False)
        self.widgets["connectButton"].set_sensitive(False)
        
        self.connection = FICSConnection("freechess.org", 23, username, password)
        self.connection.connect("connected", self.onConnected)
        self.connection.connect("disconnected", self.onDisconnected)
        self.connection.connect("error", self.showError)
        
        def pulse ():
            self.widgets["progressbar"].pulse()
            return not self.connection.isConnected()
        self.pulser = gobject.timeout_add(30, pulse)
        
        self.connection.start()

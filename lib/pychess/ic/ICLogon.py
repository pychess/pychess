from FICSConnection import FICSMainConnection, FICSHelperConnection, LogOnException
from ICLounge import ICLounge
from pychess.System import uistuff
from pychess.System.glock import glock_connect
from pychess.Utils.const import *
import gtk
import gobject
import re
import socket
import webbrowser


host = None
port = None

dialog = None
def run():
    global dialog
    
    if not dialog:
        dialog = ICLogon()
        dialog.show()
    elif dialog.lounge:
        dialog.lounge.present()
    else:
        dialog.present()

class AutoLogoutException (Exception): pass    

class ICLogon (object):
    def __init__ (self):
        self.connection = None
        self.lounge = None
        self.canceled = False
        
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
        uistuff.keep(self.widgets["nameEntry"], "usernameEntry")
        uistuff.keep(self.widgets["passEntry"], "passwordEntry")
        self.infobar = gtk.InfoBar()
        self.infobar.set_message_type(gtk.MESSAGE_WARNING)
        self.widgets["messagePanelHBox"].pack_start(self.infobar, 
            expand=False, fill=False)
        
        self.widgets["cancelButton"].connect("clicked", self.onCancel, True)
        self.widgets["stopButton"].connect("clicked", self.onCancel, False)
        self.widgets["createNewButton"].connect("clicked", self.onCreateNew)
        self.widgets["connectButton"].connect("clicked", self.onConnectClicked)
    
    def _disconnect (self):
        self.connection.close()
        self.helperconn.close()
        self.connection = None
        self.helperconn = None
        self.lounge = None
    
    def _cancel (self):
        self.connection.cancel()
        self.helperconn.cancel()
        self._disconnect()
    
    def show (self):
        self.widgets["fics_logon"].show()
    
    def present (self):
        self.widgets["fics_logon"].present()
    
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
    
    def showError (self, connection, error):
        text = str(error)
        if isinstance (error, IOError):
            title = _("Connection Error")
        elif isinstance (error, LogOnException):
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
        elif isinstance (error, AutoLogoutException):
            title = _("Auto-logout")
            text = _("You have been logged out because you were idle more than 60 minutes")
        else:
            title = str(error.__class__)
        
        self.showNormal()
        
        content_area = self.infobar.get_content_area()
        for widget in content_area:
            content_area.remove(widget)
        content = gtk.HBox()
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_DIALOG)
        content.pack_start(image, expand=False, fill=False)
        vbox = gtk.VBox()
        label = gtk.Label()
        label.props.xalign = 0
        label.props.justify = gtk.JUSTIFY_LEFT
        label.set_markup("<b><big>%s</big></b>" % title)
        vbox.pack_start(label, expand=True, fill=False)
        for line in str(text).split("\n"):
            label = gtk.Label()
            label.set_size_request(476, -1)
            label.props.selectable = True
            label.props.wrap = True
            label.props.xalign = 0
            label.props.justify = gtk.JUSTIFY_LEFT
            label.set_markup(line)
            vbox.pack_start(label, expand=True, fill=False)
        content.pack_start(vbox, expand=False, fill=False, padding=7)
        content_area.add(content)
        self.widgets["messagePanel"].show_all()
    
    def onCreateNew (self, button):
        webbrowser.open("http://www.freechess.org/Register/index.html")
        
    def onConnectClicked (self, button):
        self.canceled = False
        self.widgets["messagePanel"].hide()
        
        if self.widgets["logOnAsGuest"].get_active():
            username = "guest"
            password = ""
        else:
            username = self.widgets["nameEntry"].get_text()
            password = self.widgets["passEntry"].get_text()
        
        if port:
            ports = (port,)
        else:
            ports = self.widgets["portsEntry"].get_text()
            ports = map(int, re.findall("\d+", ports))
            if not 5000 in ports: ports.append(5000)
            if not 23 in ports: ports.append(23)
            
        self.showConnecting()
        self.host = host if host is not None else "freechess.org"
        self.connection = FICSMainConnection(self.host, ports, username, password)
        self.helperconn = FICSHelperConnection(self.connection, self.host, ports)
        self.helperconn.start()
        glock_connect(self.connection, "connected", self.onConnected)
        glock_connect(self.connection, "error", self.onConnectionError)
        glock_connect(self.connection, "connectingMsg", self.showMessage)
        self.connection.start()
    
    def onConnected (self, connection):
        self.lounge = ICLounge(connection, self.helperconn, self.host)
        self.hide()
        self.lounge.show()
        self.lounge.connect("logout", lambda iclounge: self.onLogout(connection))
        glock_connect(self.lounge, "autoLogout",
                      lambda iclounge: self.onAutologout(connection))
        
        self.showNormal()
        self.widgets["messagePanel"].hide()
    
    def onCancel (self, widget, hide):
        self.canceled = True
        
        if self.connection and self.connection.isConnecting():
            self._cancel()
            self.showNormal()
        if hide:
            self.widgets["fics_logon"].hide()
        return True
    
    def onConnectionError (self, connection, error):
        self._disconnect()
        if not self.canceled:
            self.showError(connection, error)
            self.present()
        
    def onLogout (self, connection):
        self._disconnect()
    
    def onAutologout (self, connection, alm):
        self._disconnect()
        self.showError(connection, AutoLogoutException())
        self.present()

from __future__ import absolute_import

import re
import socket
import webbrowser
from collections import defaultdict

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GObject

from pychess.System import uistuff, conf
from pychess.System.idle_add import idle_add
from .FICSConnection import FICSMainConnection, FICSHelperConnection, LogOnException
from .ICLounge import ICLounge

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


def stop():
    global dialog
    if dialog is not None:
        dialog._disconnect()


class AutoLogoutException(Exception):

    pass


def get_user_names(value=None):
    """ Split and return usernameEntry config item into registered and guest username
    """
    if value is not None:
        names = value.split("|")
    else:
        names = conf.get("usernameEntry", "").split("|")
    if len(names) == 0:
        names = ["", ""]
    elif len(names) < 2:
        names.append(names[0])
    return names


class ICLogon(object):
    def __init__(self):
        self.connection = None
        self.helperconn = None
        self.lounge = None
        self.canceled = False
        self.cids = defaultdict(list)
        self.widgets = uistuff.GladeWidgets("fics_logon.glade")
        uistuff.keepWindowSize("fics_logon",
                               self.widgets["fics_logon"],
                               defaultPosition=uistuff.POSITION_GOLDEN)
        self.widgets["fics_logon"].connect(
            'key-press-event',
            lambda w, e: e.keyval == Gdk.KEY_Escape and w.hide())

        def on_logOnAsGuest_toggled(check):
            names = get_user_names()
            self.widgets["nameEntry"].set_text(names[1] if check.get_active()
                                               else names[0])
            self.widgets["passwordLabel"].set_sensitive(not check.get_active())
            self.widgets["passEntry"].set_sensitive(not check.get_active())

        self.widgets["logOnAsGuest"].connect("toggled",
                                             on_logOnAsGuest_toggled)
        uistuff.keep(self.widgets["logOnAsGuest"], "asGuestCheck")

        as_guest = self.widgets["logOnAsGuest"]

        def user_name_get_value(entry):
            names = get_user_names()
            if as_guest.get_active():
                text = "%s|%s" % (names[0], entry.get_text())
            else:
                text = "%s|%s" % (entry.get_text(), names[1])
            return text

        def user_name_set_value(entry, value):
            names = get_user_names(value=value)
            if as_guest.get_active():
                entry.set_text(names[1])
            else:
                entry.set_text(names[0])

        uistuff.keep(self.widgets["nameEntry"], "usernameEntry",
                     user_name_get_value, user_name_set_value)
        uistuff.keep(self.widgets["passEntry"], "passwordEntry")

        # workaround to Can't type IP to FICS login dialog
        # https://github.com/pychess/pychess/issues/1360
        def host_get_value(entry):
            return entry.get_text().replace(".", "|")

        def host_set_value(entry, value):
            entry.set_text(str(value).replace("|", "."))

        uistuff.keep(self.widgets["hostEntry"], "hostEntry", host_get_value, host_set_value)

        uistuff.keep(self.widgets["autoLogin"], "autoLogin")
        self.infobar = Gtk.InfoBar()
        self.infobar.set_message_type(Gtk.MessageType.WARNING)
        # self.widgets["messagePanelHBox"].pack_start(self.infobar,
        #    expand=False, fill=False)
        self.widgets["messagePanelHBox"].pack_start(self.infobar, False, False,
                                                    0)
        self.widgets["cancelButton"].connect("clicked", self.onCancel, True)
        self.widgets["stopButton"].connect("clicked", self.onCancel, False)
        self.widgets["createNewButton"].connect("clicked", self.onCreateNew)
        self.widgets["connectButton"].connect("clicked", self.onConnectClicked)

        self.widgets["progressbar"].set_show_text(True)

    def _disconnect(self):
        for obj in self.cids:
            for cid in self.cids[obj]:
                if obj.handler_is_connected(cid):
                    obj.disconnect(cid)
        self.cids.clear()

        if self.connection is not None:
            self.connection.close()
            self.connection = None
        if self.helperconn is not None:
            self.helperconn.close()
            self.helperconn = None
        self.lounge = None

    def _cancel(self):
        if self.connection is not None:
            self.connection.cancel()
        if self.helperconn is not None:
            self.helperconn.cancel()
        self._disconnect()

    def show(self):
        self.widgets["fics_logon"].show()

    def present(self):
        self.widgets["fics_logon"].present()

    def hide(self):
        self.widgets["fics_logon"].hide()

    def showConnecting(self):
        self.widgets["progressbarBox"].show()
        self.widgets["mainbox"].set_sensitive(False)
        self.widgets["connectButton"].hide()
        self.widgets["stopButton"].show()

        def pulse():
            self.widgets["progressbar"].pulse()
            return not self.connection.isConnected()

        self.pulser = GObject.timeout_add(30, pulse)

    def showNormal(self):
        self.widgets["mainbox"].set_sensitive(True)
        self.widgets["connectButton"].show()
        self.widgets["fics_logon"].set_default(self.widgets["connectButton"])
        self.widgets["stopButton"].hide()
        self.widgets["progressbarBox"].hide()
        self.widgets["progressbar"].set_text("")
        GObject.source_remove(self.pulser)

    def showMessage(self, connection, message):
        self.widgets["progressbar"].set_text(message)

    def showError(self, connection, error):
        text = str(error)
        if isinstance(error, IOError):
            title = _("Connection Error")
        elif isinstance(error, LogOnException):
            title = _("Log on Error")
        elif isinstance(error, EOFError):
            title = _("Connection was closed")
        elif isinstance(error, socket.error):
            title = _("Connection Error")
            text = ", ".join(map(str, error.args))
        elif isinstance(error, socket.gaierror) or \
                isinstance(error, socket.herror):
            title = _("Address Error")
            text = ", ".join(map(str, error.args))
        elif isinstance(error, AutoLogoutException):
            title = _("Auto-logout")
            text = _(
                "You have been logged out because you were idle more than 60 minutes")
        else:
            title = str(error.__class__)

        self.showNormal()

        content_area = self.infobar.get_content_area()
        for widget in content_area:
            content_area.remove(widget)
        content = Gtk.HBox()
        image = Gtk.Image()
        image.set_from_stock(Gtk.STOCK_DIALOG_WARNING, Gtk.IconSize.DIALOG)
        content.pack_start(image, False, False, 0)
        vbox = Gtk.VBox()
        label = Gtk.Label()
        label.props.xalign = 0
        label.props.justify = Gtk.Justification.LEFT
        label.set_markup("<b><big>%s</big></b>" % title)
        vbox.pack_start(label, True, False, 0)
        for line in str(text).split("\n"):
            label = Gtk.Label()
            label.set_size_request(476, -1)
            label.props.selectable = True
            label.props.wrap = True
            label.props.xalign = 0
            label.props.justify = Gtk.Justification.LEFT
            label.set_markup(line)
            vbox.pack_start(label, True, False, 0)
        content.pack_start(vbox, False, False, 7)
        content_area.add(content)
        self.widgets["messagePanel"].show_all()

    def onCreateNew(self, button):
        webbrowser.open("http://www.freechess.org/Register/index.html")

    def onConnectClicked(self, button):
        self.canceled = False
        self.widgets["messagePanel"].hide()

        if self.widgets["logOnAsGuest"].get_active():
            username = self.widgets["nameEntry"].get_text()
            password = ""
        else:
            username = self.widgets["nameEntry"].get_text()
            password = self.widgets["passEntry"].get_text()

        if port:
            ports = (port, )
        else:
            ports = self.widgets["portsEntry"].get_text()
            ports = list(map(int, re.findall("\d+", ports)))
            if 5000 not in ports:
                ports.append(5000)
            if 23 not in ports:
                ports.append(23)
        alternate_host = self.widgets["hostEntry"].get_text()

        self.showConnecting()
        self.host = host if host is not None else alternate_host if alternate_host else "freechess.org"
        self.connection = FICSMainConnection(self.host, ports, username,
                                             password)
        for signal, callback in (("connected", self.onConnected),
                                 ("error", self.onConnectionError),
                                 ("connectingMsg", self.showMessage)):
            self.cids[self.connection].append(self.connection.connect(
                signal, callback))
        self.connection.start()

        self.helperconn = FICSHelperConnection(self.connection, self.host, ports)
        self.helperconn.connect("error", self.onHelperConnectionError)
        self.helperconn.start()

    @idle_add
    def onHelperConnectionError(self, connection, error):
        if self.helperconn is not None:
            dialog = Gtk.MessageDialog(type=Gtk.MessageType.QUESTION,
                                       buttons=Gtk.ButtonsType.YES_NO)
            dialog.set_markup(_("Guest logins disabled by FICS server"))
            text = "PyChess can maintain users status and games list only if it changes\n\
            'open', 'gin' and 'availinfo' user variables.\n\
            Do you enable to set these variables on?"
            dialog.format_secondary_text(text)
            response = dialog.run()
            dialog.destroy()

            self.helperconn.cancel()
            self.helperconn.close()
            self.helperconn = None

            set_user_vars = response == Gtk.ResponseType.YES
            self.connection.start_helper_manager(set_user_vars)

    @idle_add
    def onConnected(self, connection):
        self.lounge = ICLounge(connection, self.helperconn, self.host)
        self.hide()
        self.lounge.show()
        self.lounge.connect("logout",
                            lambda iclounge: self.onLogout(connection))
        self.cids[self.lounge].append(self.lounge.connect(
            "autoLogout", lambda lounge: self.onAutologout(connection)))

        self.showNormal()
        self.widgets["messagePanel"].hide()

    @idle_add
    def onCancel(self, widget, hide):
        self.canceled = True

        if self.connection and self.connection.isConnecting():
            self._cancel()
            self.showNormal()
        if hide:
            self.widgets["fics_logon"].hide()

    @idle_add
    def onConnectionError(self, connection, error):
        self._disconnect()
        if not self.canceled:
            self.showError(connection, error)
            self.present()

    @idle_add
    def onLogout(self, connection):
        self._disconnect()

    @idle_add
    def onAutologout(self, connection):
        self._disconnect()
        self.showError(connection, AutoLogoutException())
        self.present()

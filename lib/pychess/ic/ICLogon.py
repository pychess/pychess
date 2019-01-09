
import asyncio
import re
import socket
import webbrowser
from collections import defaultdict

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject

from pychess.compat import create_task
from pychess.System import uistuff, conf
from pychess.widgets import mainwindow
from pychess.ic.FICSConnection import FICSMainConnection, FICSHelperConnection, LogOnException
from pychess.perspectives import perspective_manager

host = None
port = None

dialog = None


def run():
    global dialog
    dialog.widgets["fics_logon"].set_transient_for(mainwindow())

    if dialog.lounge:
        dialog.lounge.present()
    else:
        dialog.present()


def stop():
    global dialog
    if dialog is not None:
        dialog._disconnect()


class AutoLogoutException(Exception):

    pass


class ICLogon:
    def __init__(self):
        self.connection = None
        self.helperconn = None
        self.connection_task = None
        self.helperconn_task = None
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

        self.ics = "FICS"
        self.as_guest = self.widgets["logOnAsGuest"]

        self.widgets["logOnAsGuest"].connect("toggled", self.on_logOnAsGuest_toggled)

        def on_username_changed(widget):
            conf.set("usernameEntry", self.user_name_get_value(widget), section=self.ics)
        self.widgets["nameEntry"].connect("changed", on_username_changed)

        def on_password_changed(widget):
            conf.set("passwordEntry", widget.get_text(), section=self.ics)
        self.widgets["passEntry"].connect("changed", on_password_changed)

        def on_host_changed(widget):
            conf.set("hostEntry", self.host_get_value(widget), section=self.ics)
        self.widgets["hostEntry"].connect("changed", on_host_changed)

        self.widgets["timesealCheck"].connect("toggled", self.on_timeseal_toggled)

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

    def get_user_names(self, value=None):
        """ Split and return usernameEntry config item into registered and guest username
        """
        if value is not None:
            names = value.split("|")
        else:
            names = conf.get("usernameEntry", section=self.ics).split("|")
        if len(names) == 0:
            names = ["", ""]
        elif len(names) < 2:
            names.append(names[0])
        return names

    def user_name_get_value(self, entry):
        names = self.get_user_names()
        if self.as_guest.get_active():
            text = "%s|%s" % (names[0], entry.get_text())
        else:
            text = "%s|%s" % (entry.get_text(), names[1])
        return text

    def user_name_set_value(self, entry, value):
        names = self.get_user_names(value=value)
        if self.as_guest.get_active():
            entry.set_text(names[1])
        else:
            entry.set_text(names[0])

    # workaround to FICS Password input doesnt handle strings starting with a number
    # https://github.com/pychess/pychess/issues/1375
    def password_set_value(self, entry, value):
        entry.set_text(str(value))

    # workaround to Can't type IP to FICS login dialog
    # https://github.com/pychess/pychess/issues/1360
    def host_get_value(self, entry):
        return entry.get_text().replace(".", "|")

    def host_set_value(self, entry, value):
        entry.set_text(str(value).replace("|", "."))

    def on_logOnAsGuest_toggled(self, widget):
        names = self.get_user_names()
        self.widgets["nameEntry"].set_text(names[1] if widget.get_active() else names[0])
        if self.ics == "ICC":
            self.widgets["nameLabel"].set_sensitive(not widget.get_active())
            self.widgets["nameEntry"].set_sensitive(not widget.get_active())
        else:
            self.widgets["nameLabel"].set_sensitive(True)
            self.widgets["nameEntry"].set_sensitive(True)
        self.widgets["passwordLabel"].set_sensitive(not widget.get_active())
        self.widgets["passEntry"].set_sensitive(not widget.get_active())
        conf.set("asGuestCheck", widget.get_active(), section=self.ics)

    def on_timeseal_toggled(self, widget):
        conf.set("timesealCheck", widget.get_active(), section=self.ics)

    def on_ics_combo_changed(self, combo):
        tree_iter = combo.get_active_iter()
        if tree_iter is not None:
            model = combo.get_model()
            self.ics = model[tree_iter][0]
            # print("Selected: %s" % self.ics)
            self.widgets["logOnAsGuest"].set_active(conf.get("asGuestCheck", section=self.ics))
            self.on_logOnAsGuest_toggled(self.widgets["logOnAsGuest"])
            self.user_name_set_value(self.widgets["nameEntry"], conf.get("usernameEntry", section=self.ics))
            self.password_set_value(self.widgets["passEntry"], conf.get("passwordEntry", section=self.ics))
            self.host_set_value(self.widgets["hostEntry"], conf.get("hostEntry", section=self.ics))
            self.widgets["timesealCheck"].set_active(conf.get("timesealCheck", section=self.ics))
            self.on_timeseal_toggled(self.widgets["timesealCheck"])

    def _disconnect(self):
        for obj in self.cids:
            for cid in self.cids[obj]:
                if obj.handler_is_connected(cid):
                    obj.disconnect(cid)
        self.cids.clear()

        if self.connection is not None:
            self.connection.close()
            if not self.connection_task.cancelled():
                self.connection_task.cancel()
            self.connection = None
        if self.helperconn is not None:
            self.helperconn.close()
            if not self.helperconn_task.cancelled():
                self.helperconn_task.cancel()
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
            if self.connection is None:
                return False
            else:
                return not self.connection.isConnected()

        self.pulser = GLib.timeout_add(30, pulse)

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
        if self.widgets["hostEntry"].get_text() == "chessclub.com":
            webbrowser.open("https://store.chessclub.com/customer/account/create/")
        else:
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

        timeseal = self.widgets["timesealCheck"].get_active()

        self.showConnecting()
        self.host = host if host is not None else alternate_host if alternate_host else "freechess.org"
        self.connection = FICSMainConnection(self.host, ports, timeseal, username, password)
        for signal, callback in (("connected", self.onConnected),
                                 ("error", self.onConnectionError),
                                 ("connectingMsg", self.showMessage)):
            self.cids[self.connection].append(self.connection.connect(signal, callback))
        self.main_connected_event = asyncio.Event()
        self.connection_task = create_task(self.connection.start())

        # guest users are rather limited on ICC (helper connection is useless)
        if self.host not in ("localhost", "127.0.0.1", "chessclub.com"):
            self.helperconn = FICSHelperConnection(self.connection, self.host, ports, timeseal)
            self.helperconn.connect("error", self.onHelperConnectionError)

            @asyncio.coroutine
            def coro():
                yield from self.main_connected_event.wait()
                yield from self.helperconn.start()

            self.helperconn_task = create_task(coro())

    def onHelperConnectionError(self, connection, error):
        if self.helperconn is not None:
            dialog = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.QUESTION,
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

            @asyncio.coroutine
            def coro():
                yield from self.main_connected_event.wait()
                self.connection.start_helper_manager(set_user_vars)
            create_task(coro())

    def onConnected(self, connection):
        self.main_connected_event.set()
        if connection.ICC:
            self.connection.start_helper_manager(True)

        self.lounge = perspective_manager.get_perspective("fics")
        self.lounge.open_lounge(connection, self.helperconn, self.host)
        self.hide()
        self.lounge.show()
        self.lounge.connect("logout",
                            lambda iclounge: self.onLogout(connection))
        self.cids[self.lounge].append(self.lounge.connect(
            "autoLogout", lambda lounge: self.onAutologout(connection)))

        self.showNormal()
        self.widgets["messagePanel"].hide()

    def onCancel(self, widget, hide):
        self.canceled = True

        if self.connection and self.connection.isConnecting():
            self._cancel()
            self.showNormal()
        if hide:
            self.widgets["fics_logon"].hide()

    def onConnectionError(self, connection, error):
        self._disconnect()
        if not self.canceled:
            self.showError(connection, error)
            self.present()

    def onLogout(self, connection):
        self._disconnect()

    def onAutologout(self, connection):
        self._disconnect()
        self.showError(connection, AutoLogoutException())
        self.present()

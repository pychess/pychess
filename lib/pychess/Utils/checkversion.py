from __future__ import print_function

import ssl
import json
from threading import Thread

from gi.repository import GLib, Gtk

from pychess import VERSION
from pychess.compat import Request, urlopen, URLError

URL = "https://api.github.com/repos/pychess/pychess/releases/latest"
LINK = "https://github.com/pychess/pychess/releases"


def checkversion():

    def worker():
        new_version = None
        req = Request(URL)
        try:
            context = ssl._create_unverified_context()
            response = urlopen(req, context=context, timeout=1)
        except URLError as err:
            if hasattr(err, 'reason'):
                print('We failed to reach the server.')
                print('Reason: ', err.reason)
            elif hasattr(err, 'code'):
                print('The server couldn\'t fulfill the request.')
                print('Error code: ', err.code)
        else:
            new_version = json.loads(response.read())["name"]

        if new_version is not None and VERSION.split(".") < new_version.split("."):
            GLib.idle_add(notify, new_version)

    def notify(new_version):
        msg_dialog = Gtk.MessageDialog(type=Gtk.MessageType.INFO,
                                       buttons=Gtk.ButtonsType.OK)

        msg = _("<b>New version %s is available!</b>" % new_version)
        msg_dialog.set_markup(msg)
        msg_dialog.format_secondary_markup('<a href="%s">%s</a>' % (LINK, LINK))

        msg_dialog.connect("response", lambda msg_dialog, a: msg_dialog.hide())
        msg_dialog.show()

    t = Thread(target=worker)
    t.daemon = True
    t.start()

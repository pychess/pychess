import asyncio
import json
from urllib.error import URLError

from gi.repository import GLib, Gtk

from pychess import VERSION
from pychess.System.fetch import fetch
from pychess.widgets import mainwindow

URL = "https://api.github.com/repos/pychess/pychess/releases/latest"
LINK = "https://github.com/pychess/pychess/releases"


@asyncio.coroutine
def checkversion():
    new_version = None
    try:
        response = yield from fetch(URL)
    except URLError as err:
        if hasattr(err, 'reason'):
            print('We failed to reach the server.')
            print('Reason: ', err.reason)
        elif hasattr(err, 'code'):
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', err.code)
    else:
        str_response = response.decode('utf-8')
        new_version = json.loads(str_response)["name"]

    def notify(new_version):
        msg_dialog = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.INFO,
                                       buttons=Gtk.ButtonsType.OK)

        msg = _("<b>New version %s is available!</b>" % new_version)
        msg_dialog.set_markup(msg)
        msg_dialog.format_secondary_markup('<a href="%s">%s</a>' % (LINK, LINK))

        msg_dialog.connect("response", lambda msg_dialog, a: msg_dialog.hide())
        msg_dialog.show()

    if new_version is not None and VERSION.split(".") < new_version.split("."):
        GLib.idle_add(notify, new_version)

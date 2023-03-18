import os.path
import json

from gi.repository import GLib, Gtk

from pychess import VERSION
from pychess.widgets import mainwindow
from pychess.System import download_file_async, prefix

URL = "https://api.github.com/repos/pychess/pychess/releases/latest"
LINK = "https://github.com/pychess/pychess/releases"


def isgit():
    return os.path.isdir(prefix.addDataPrefix(".git"))


async def checkversion():
    if isgit():
        return

    new_version = None

    filename = await download_file_async(URL)

    if filename is not None:
        with open(filename, encoding="utf-8") as f:
            new_version = json.loads(f.read())["name"]

    def notify(new_version):
        msg_dialog = Gtk.MessageDialog(
            mainwindow(), type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK
        )

        msg = _("<b>New version %s is available!</b>" % new_version)
        msg_dialog.set_markup(msg)
        msg_dialog.format_secondary_markup(f'<a href="{LINK}">{LINK}</a>')

        msg_dialog.connect("response", lambda msg_dialog, a: msg_dialog.hide())
        msg_dialog.show()

    if new_version is not None and VERSION.split(".") < new_version.split("."):
        GLib.idle_add(notify, new_version)

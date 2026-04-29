import sys

import gi

gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk", "3.0")

from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GdkPixbuf

from pychess.System.Log import log
from pychess.System.prefix import addDataPrefix

_icon_theme = None


def _get_icon_theme():
    global _icon_theme
    if _icon_theme is None:
        _icon_theme = Gtk.IconTheme.get_default()
    return _icon_theme


def load_icon(size, *alternatives):
    alternatives = list(alternatives)
    name = alternatives.pop(0)
    try:
        return _get_icon_theme().load_icon(name, size, Gtk.IconLookupFlags.USE_BUILTIN)
    except Exception:
        if alternatives:
            return load_icon(size, *alternatives)
        log.warning("no %s icon in icon-theme-gnome" % name)


# Gdk.Pixbuf.new_from_file() doesn't work on Windows if path contains non ascii chars
def get_pixbuf(path, size=None):
    path = addDataPrefix(path)
    if sys.platform != "win32":
        if size is None:
            return GdkPixbuf.Pixbuf.new_from_file(path)
        return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)

    file = Gio.File.new_for_path(path)
    stream = file.read(None)
    try:
        if size is None:
            return GdkPixbuf.Pixbuf.new_from_stream(stream, None)
        else:
            return GdkPixbuf.Pixbuf.new_from_stream_at_scale(
                stream, size, size, True, None
            )
    finally:
        stream.close(None)

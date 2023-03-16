from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GdkPixbuf

from pychess.System.Log import log
from pychess.System.prefix import addDataPrefix

it = Gtk.IconTheme.get_default()


def load_icon(size, *alternatives):
    alternatives = list(alternatives)
    name = alternatives.pop(0)
    try:
        return it.load_icon(name, size, Gtk.IconLookupFlags.USE_BUILTIN)
    except Exception:
        if alternatives:
            return load_icon(size, *alternatives)
        log.warning("no %s icon in icon-theme-gnome" % name)


# Gdk.Pixbuf.new_from_file() doesn't work on Windows if path contains non ascii chars
def get_pixbuf(path, size=None):
    file = Gio.File.new_for_path(addDataPrefix(path))
    if size is None:
        return GdkPixbuf.Pixbuf.new_from_stream(file.read(None), None)
    else:
        return GdkPixbuf.Pixbuf.new_from_stream_at_scale(
            file.read(None), size, size, True, None
        )

from gi.repository import Gtk
from pychess.System.Log import log

it = Gtk.IconTheme.get_default()
def load_icon(size, *alternatives):
    alternatives = list(alternatives)
    name = alternatives.pop(0)
    try:
        return it.load_icon(name, size, Gtk.IconLookupFlags.USE_BUILTIN)
    except:
        if alternatives:
            return load_icon(size, *alternatives)
        log.warning("no %s icon in icon-theme-gnome" % name)

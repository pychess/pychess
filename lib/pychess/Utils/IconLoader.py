from gtk import icon_theme_get_default, ICON_LOOKUP_USE_BUILTIN
from pychess.System.Log import log

it = icon_theme_get_default()
def load_icon(size, *alternatives):
    alternatives = list(alternatives)
    name = alternatives.pop(0)
    try:
        return it.load_icon(name, size, ICON_LOOKUP_USE_BUILTIN)
    except:
        if alternatives:
            return load_icon(size, *alternatives)
        log.warning("no %s icon in icon-theme-gnome" % name)

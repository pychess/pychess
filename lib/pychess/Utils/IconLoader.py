from gtk import icon_theme_get_default, ICON_LOOKUP_USE_BUILTIN

it = icon_theme_get_default()
def load_icon(size, name, alternative=None):
    try:
        return it.load_icon(name, size, ICON_LOOKUP_USE_BUILTIN)
    except:
        if alternative is not None:
            try:
                return it.load_icon(alternative, size, ICON_LOOKUP_USE_BUILTIN)
            except:
                print "no %s icon in icon-theme-gnome" % alternative
        else:
            print "no %s icon in icon-theme-gnome" % name

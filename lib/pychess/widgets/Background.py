from os import path

from gi.repository import Gtk
from gi.repository import Gdk
import cairo

from pychess.System.prefix import addDataPrefix, addUserCachePrefix

CLEARPATH = addDataPrefix("glade/clear.png")
surface = None
provider = None
loldcolor = None
doldcolor = None

def giveBackground (widget):    
    widget.connect("draw", expose)
    widget.connect("style-updated", newtheme)

def expose (widget, context):    
    cr = widget.get_window().cairo_create()

    x = widget.get_allocation().x
    y = widget.get_allocation().y
    width = widget.get_allocation().width
    height = widget.get_allocation().height
    cr.rectangle (x, y, width, height)
    if not surface:
        newtheme(widget)
    cr.set_source_surface(surface, 0, 0)
    pattern = cr.get_source()
    pattern.set_extend(cairo.EXTEND_REPEAT)
    cr.fill()

def newtheme (widget):
    global surface, provider, loldcolor, doldcolor
    
    sc = widget.get_style_context()

    # get colors from theme

    # bg color
    found, bgcol = sc.lookup_color("bg_color")
    if not found:        
        found, bgcol = sc.lookup_color("theme_bg_color")
        if not found:
            # fallback value
            bgcol = Gdk.RGBA(red=0.929412, green=0.929412, blue=0.929412, alpha=1.0)

    # bg selected color
    found, bgsel = sc.lookup_color("theme_selected_bg_color")
    if not found:
        # fallback value
        bgsel = Gdk.RGBA(red=0.290, green=0.565, blue=0.851, alpha=1.0)

    # fg color
    found, fgcol = sc.lookup_color("fg_color")
    if not found:
        found, fgcol = sc.lookup_color("theme_fg_color")
        if not found:            
            fgcol= Gdk.RGBA(red=0.180392, green=0.203922, blue=0.211765, alpha=1.000000)

    def get_col(col, mult):
        r = col.red * mult
        g = col.green * mult
        b = col.blue * mult
        if r > 1.0: r = 1.0
        if g > 1.0: g = 1.0
        if b > 1.0: b = 1.0
        return Gdk.RGBA(r, g, b, 1.0)

    # derive other colors
    bgacol = get_col(bgcol, 0.9)           # bg_active    
    dcol = get_col(bgcol, 0.7)             # dark
    darksel = get_col(bgsel, 0.71)         # dark selected
    dpcol = get_col(bgcol, 0.71)           # dark prelight
    dacol = get_col(dcol, 0.9)             # dark_active
    lcol = get_col(bgcol, 1.3)             # light color
    fgsel = Gdk.RGBA(1.0, 1.0, 1.0, 1.0)   # fg selected
    fgpcol = get_col(fgcol, 1.054)         # fg prelight
    fgacol = Gdk.RGBA(0.0, 0.0, 0.0, 1.0)  # fg active

    # return hex string #rrggbb
    def color_to_string(color): 
        red, green, blue = color        
        return "#%02X%02X%02X" % (int(red * 255), int(green * 255), int(blue * 255))

    # convert to #rrggbb
    bg_color = color_to_string((bgcol.red, bgcol.green, bgcol.blue))
    bg_prelight = bg_color
    bg_active = color_to_string((bgacol.red, bgacol.green, bgacol.blue))
    bg_selected = color_to_string((bgsel.red, bgsel.green, bgsel.blue))
    dark_color = color_to_string((dcol.red, dcol.green, dcol.blue))
    dark_prelight = color_to_string((dpcol.red, dpcol.green, dpcol.blue))    
    dark_active = color_to_string((dacol.red, dacol.green, dacol.blue))
    dark_selected = color_to_string((darksel.red, darksel.green, darksel.blue))
    light_color = color_to_string((lcol.red, lcol.green, lcol.blue))
    fg_color = color_to_string((fgcol.red, fgcol.green, fgcol.blue))
    fg_active = color_to_string((fgacol.red, fgacol.green, fgacol.blue))
    fg_prelight = color_to_string((fgpcol.red, fgpcol.green, fgpcol.blue))
    fg_selected = color_to_string((fgsel.red, fgsel.green, fgsel.blue))

    data = "@define-color p_bg_color " + bg_color + ";" \
           "@define-color p_bg_prelight " +  bg_prelight + ";" \
           "@define-color p_bg_active " + bg_active + ";" \
           "@define-color p_bg_selected " + bg_selected + ";" \
           "@define-color p_dark_color " + dark_color + ";" \
           "@define-color p_dark_prelight " + dark_prelight + ";" \
           "@define-color p_dark_active " + dark_active + ";" \
           "@define-color p_dark_selected " + dark_selected + ";" \
           "@define-color p_light_color " + light_color + ";" \
           "@define-color p_fg_color " + fg_color + ";" \
           "@define-color p_fg_prelight " + fg_prelight + ";" \
           "@define-color p_fg_selected " + fg_selected + ";" \
           "@define-color p_fg_active " + fg_active + ";"

    if provider is not None:        
        sc.remove_provider_for_screen(Gdk.Screen.get_default(), provider)

    provider = Gtk.CssProvider.new()
    provider.load_from_data(data)
    sc.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    lnewcolor = bgcol
    dnewcolor = dcol

    # check if changed
    if loldcolor:
        if lnewcolor.red   == loldcolor.red and \
           lnewcolor.green == loldcolor.green and \
           lnewcolor.blue  == loldcolor.blue and \
           dnewcolor.red   == doldcolor.red and \
           dnewcolor.green == doldcolor.green and \
           dnewcolor.blue  == doldcolor.blue:
            return

    loldcolor = lnewcolor
    doldcolor = dnewcolor

    # global colors have been set up
    # now set colors on startup panel
    bool1, lnewcolor = sc.lookup_color("p_bg_color")    
    bool1, dnewcolor = sc.lookup_color("p_dark_color")
  
    colors = [
        int(lnewcolor.red * 255), int(lnewcolor.green * 255), int(lnewcolor.blue * 255),
        int(dnewcolor.red * 255), int(dnewcolor.green * 255), int(dnewcolor.blue * 255)
    ]

    # Check if a cache has been saved
    temppng = addUserCachePrefix("temp.png")
    if path.isfile(temppng):
        f = open(temppng, "rb")
        # Check if the cache was made while using the same theme
        if [ord(c) for c in f.read(6)] == colors:
            surface = cairo.ImageSurface.create_from_png(f)
            return
    
    # Get mostly transparant shadowy image
    imgsurface = cairo.ImageSurface.create_from_png(CLEARPATH)
    AVGALPHA = 108/255.
    
    surface = cairo.ImageSurface(cairo.FORMAT_RGB24,
            imgsurface.get_width(), imgsurface.get_height())
    ctx = cairo.Context (surface)
    if lnewcolor.blue*65535 - dnewcolor.blue*65535 > 0:
        a = dnewcolor.red*65535/(3*(lnewcolor.blue*65535 - dnewcolor.blue*65535)*(1-AVGALPHA))
        ctx.set_source_rgb(
            lnewcolor.red/2  + dnewcolor.red*a/2,
            lnewcolor.green/2 + dnewcolor.green*a/2,
            lnewcolor.blue/2  + dnewcolor.blue*a/2)
        ctx.paint()
    ctx.set_source_surface(imgsurface, 0, 0)
    ctx.paint_with_alpha(.8)
    
    # Save a cache for later use. Save 'newcolor' in the frist three pixels
    # to check for theme changes between two instances
    f = open(temppng, "wb")
    for color in colors:
        f.write(chr(color))
    surface.write_to_png(f)
    

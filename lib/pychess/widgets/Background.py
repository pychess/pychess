from os import path

from gi.repository import Gtk
from gi.repository import Gdk
import cairo

from pychess.System.prefix import addDataPrefix, addUserCachePrefix

CLEARPATH = addDataPrefix("glade/clear.png")
surface = None

def giveBackground (widget):    
    widget.connect("draw", expose)
    widget.connect("style-set", newtheme)

def expose (widget, context):    
    cr = widget.get_window().cairo_create()

    x = widget.get_allocation().x
    y = widget.get_allocation().y
    width = widget.get_allocation().width
    height = widget.get_allocation().height
    cr.rectangle (x, y, width, height)
    #cr.rectangle (event.area.x, event.area.y, event.area.width, event.area.height)
    if not surface:
        newtheme(widget, None)
    cr.set_source_surface(surface, 0, 0)
    pattern = cr.get_source()
    pattern.set_extend(cairo.EXTEND_REPEAT)
    cr.fill()

def newtheme (widget, oldstyle):
    global surface  
    
    sc = widget.get_style_context()
    bool1, lnewcolor = sc.lookup_color("bg_color")    
    bool1, dnewcolor = sc.lookup_color("dark_color")
  
    if oldstyle:
        loldcolor = oldstyle.bg[Gtk.StateType.NORMAL]
        doldcolor = oldstyle.dark[Gtk.StateType.NORMAL]
        if lnewcolor.red   == loldcolor.red and \
           lnewcolor.green == loldcolor.green and \
           lnewcolor.blue  == loldcolor.blue and \
           dnewcolor.red   == doldcolor.red and \
           dnewcolor.green == doldcolor.green and \
           dnewcolor.blue  == doldcolor.blue:
            return    
  
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
    

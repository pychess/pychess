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

    # FIXME   
    """    
    #lnewcolor = widget.get_style().bg[Gtk.StateType.NORMAL]
    context = widget.get_style_context()
    lnewcolor = context.get_background_color(Gtk.StateType.NORMAL)

    #dnewcolor = widget.get_style().dark[Gtk.StateType.NORMAL]
    dnewcolor = context.get_dark_color(Gtk.StateType.NORMAL)
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
        lnewcolor.red/256, lnewcolor.green/256, lnewcolor.blue/256,
        dnewcolor.red/256, dnewcolor.green/256, dnewcolor.blue/256
    ]
    """

    lnewcolor = Gdk.Color(237, 237, 237)
    dnewcolor = Gdk.Color(166, 166, 166)

    colors = [
        lnewcolor.red/256, lnewcolor.green/256, lnewcolor.blue/256,
        dnewcolor.red/256, dnewcolor.green/256, dnewcolor.blue/256
    ]
   
    #colors = [
    #    0.929, 0.929, 0.929,
    #    0.651, 0.651, 0.651
    #]

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
    if lnewcolor.blue-dnewcolor.blue > 0:
        a = dnewcolor.red/(3*(lnewcolor.blue-dnewcolor.blue)*(1-AVGALPHA))
        ctx.set_source_rgb(
            lnewcolor.red/65535./2  + dnewcolor.red/65535.*a/2,
            lnewcolor.green/65535./2 + dnewcolor.green/65535.*a/2,
            lnewcolor.blue/65535./2  + dnewcolor.blue/65535.*a/2)
        ctx.paint()
    ctx.set_source_surface(imgsurface, 0, 0)
    ctx.paint_with_alpha(.8)
    
    # Save a cache for later use. Save 'newcolor' in the frist three pixels
    # to check for theme changes between two instances
    f = open(temppng, "wb")
    for color in colors:
        f.write(chr(color))
    surface.write_to_png(f)
    

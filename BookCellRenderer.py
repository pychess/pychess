import gtk, gobject

width, height = 80, 23
class BookCellRenderer (gtk.GenericCellRenderer):
    __gproperties__ = {
        "data": (gobject.TYPE_PYOBJECT, "Data", "Data", gobject.PARAM_READWRITE),
    }
    
    def __init__(self):
        self.__gobject_init__()
        self.data = None
        
    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)
        
    def do_get_property(self, pspec):
        return getattr(self, pspec.name)
        
    def on_render(self, window, widget, background_area, cell_area, expose_area, flags):
        if not self.data: return
        cairo = window.cairo_create()
        w,d,l = self.data
        paintGraph(cairo, w, d, l, cell_area)
       
    def on_get_size(self, widget, cell_area=None):
        return (0, 0, width, height)
            
gobject.type_register(BookCellRenderer)

from math import ceil

def paintGraph (cairo,win,draw,loss,rect):
    x,y,w,h = rect.x, rect.y, rect.width, rect.height

    cairo.save()
    cairo.rectangle(x,y,ceil(win*w),h); cairo.clip()
    pathBlock(cairo, x,y,w,h)
    cairo.set_source_rgb(0.9,0.9,0.9)
    cairo.fill()
    cairo.restore()
    
    cairo.save()
    cairo.rectangle(x+win*w,y,ceil(draw*w),h); cairo.clip()
    pathBlock(cairo, x,y,w,h)
    cairo.set_source_rgb(0.45,0.45,0.45)
    cairo.fill()
    cairo.restore()
    
    cairo.save()
    cairo.rectangle(x+win*w+draw*w,y,loss*w,h); cairo.clip()
    pathBlock(cairo, x,y,w,h)
    cairo.set_source_rgb(0,0,0)
    cairo.fill()
    cairo.restore()
    
    cairo.save()
    cairo.rectangle(x,y,w,h); cairo.clip()
    pathBlock(cairo, x,y,w,h)
    cairo.set_source_rgb(1,1,1)
    cairo.stroke()
    cairo.restore()

def pathBlock (cairo, x,y,w,h):
    cairo.move_to(x+10, y)
    cairo.rel_line_to(w-20, 0)
    cairo.rel_curve_to(10, 0, 10, 0, 10, 10)
    cairo.rel_line_to(0, 3)
    cairo.rel_curve_to(0, 10, 0, 10, -10, 10)
    cairo.rel_line_to(-w+20, 0)
    cairo.rel_curve_to(-10, 0, -10, 0, -10, -10)
    cairo.rel_line_to(0, -3)
    cairo.rel_curve_to(0, -10, 0, -10, 10, -10)





















#
# Some ideas to get this working using a pixbuf instead of a customrenderer
# Sadly cairo / gtk support is not too good yet :(
#

#surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 80, 23)
#context = gtk.gdk.CairoContext(cairo.Context(surface))
#paintGraph(context,win,draw,loss,80)
#pixbuf = surfaceToPixbuf(surface)

def getCairoPixbuf (width, height):
    #Doesn't work :(
    data = array.array('c', 'a' * width * height * 4)
    surface = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, width, height)
    pixbuf = gtk.gdk.pixbuf_new_from_data(data, gtk.gdk.COLORSPACE_RGB, True, 8, width, height, 0)
    context = gtk.gdk.CairoContext(cairo.Context(surface))
    return (cairo, pixbuf)

def connectToPixbuf (pixbuf, cairo):
    #Doesn't work :(
    context.set_source_pixbuf(pixbuf, 0, 0)

class Fileadapter (file):
    #Doesn't work :(
    def __init__ (self, loader):
        file.__init__(self, "/tmp/nothing", "w")
        self.loader = loader
    def write(self,s):
        self.loader.write(s)
def surfaceToPixbuf2 (surface):
    loader = gtk.gdk.PixbufLoader()
    f = Fileadapter(loader)
    surface.write_to_png(f)
    pixbuf = loader.get_pixbuf()
    loader.close()
    return pixbuf

def surfaceToPixbuf (surface):
    #Don't wanna write to disk :(
    surface.write_to_png("/tmp/surface.png")
    pixbuf = gtk.gdk.pixbuf_new_from_file("/tmp/surface.png")
    return pixbuf

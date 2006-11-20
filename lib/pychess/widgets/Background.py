import gtk, cairo
from os import path
from pychess.Utils.const import prefix
from array import array

def INT_MULT (a, b):
	c = a * b + 0x80
	return ((c >> 8) + c) >> 8

class Background (gtk.DrawingArea):
    
    def __init__ (self):
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.expose)
        self.connect("style-set", self.newtheme)
        self.clearpath = prefix("glade/clear.png")
        
    def expose (self, widget, event):
        cr = widget.window.cairo_create()
        cr.rectangle (event.area.x, event.area.y, event.area.width, event.area.height)
        cr.set_source_surface(self.surface, 0, 0)
        pattern = cr.get_source()
        #pattern.set_filter(cairo.FILTER_GAUSSIAN)
        pattern.set_extend(cairo.EXTEND_REPEAT)
        cr.fill()
    
    def newtheme (self, widget, oldstyle):
        
        lnew = self.get_style().bg[gtk.STATE_NORMAL]
        dnew = self.get_style().dark[gtk.STATE_NORMAL]
        
        if oldstyle:
            lold = oldstyle.bg[gtk.STATE_NORMAL]
            dold = oldstyle.dark[gtk.STATE_NORMAL]
            
            if lnew.red == lold.red and \
               lnew.green == lold.green and \
               lnew.blue == lold.blue and \
               dnew.red == dold.red and \
               dnew.green == dold.green and \
               dnew.blue == dold.blue:
                return
        
        light = map(lambda x: x/256, (lnew.red, lnew.green, lnew.blue))
        dark = map(lambda x: x/256, (dnew.red, dnew.green, dnew.blue))
        
        surface = cairo.ImageSurface.create_from_png(self.clearpath)
        buffer = surface.get_data_as_rgba()
        
        data = array ('c', 'a' * surface.get_width() * surface.get_height() * 4)
        surf = cairo.ImageSurface.create_for_data (data, cairo.FORMAT_ARGB32,
                surface.get_width(), surface.get_height(), surface.get_stride())
        ctx = cairo.Context (surf)
        ctx.rectangle (0, 0, surface.get_width(), surface.get_height())
        ctx.set_source_surface(surface, 0, 0)
        ctx.fill()
        
        dark.reverse()
        dic = {}
        for s in xrange(0, len(data), 4):
            for i in xrange (3):
                if not data[s+i] in dic:
                    dic [data[s+i]] = {i: chr( (dark[i] + ord(data[s+i])) /3 )}
                elif not i in dic [data[s+i]]:
                    dic [data[s+i]][i] = chr( (dark[i] + ord(data[s+i])) /3 )
                data [s+i] = dic[data [s+i]][i]
        
        self.surface = cairo.ImageSurface.create_for_data (
            data, cairo.FORMAT_ARGB32,
            surface.get_width(), surface.get_height(),
            surface.get_stride())

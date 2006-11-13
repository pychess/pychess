import gtk, cairo
from os import path

class Background (gtk.DrawingArea):
    
    def __init__ (self):
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.expose)
        self.connect("style-set", self.newtheme)
        
    def expose (self, widget, event):
        cr = widget.window.cairo_create()
        clearpath = path.join(path.split(__file__)[0], "../glade/clear.png")
        surface = cairo.ImageSurface.create_from_png(clearpath)
        cr.rectangle (event.area.x, event.area.y, event.area.width, event.area.height)
        cr.set_source_surface(surface, 0, 0)
        pattern = cr.get_source()
        pattern.set_filter(cairo.FILTER_GAUSSIAN)
        pattern.set_extend(cairo.EXTEND_REPEAT)
        cr.fill()
    
    def newtheme (self, widget, oldstyle):
        
        cnew = self.get_style().bg[gtk.STATE_NORMAL]
        
        if oldstyle:
            cold = oldstyle.bg[gtk.STATE_NORMAL]
            
            if cnew.red == cold.red and \
               cnew.green == cold.green and \
               cnew.blue == cold.blue:
                return
        
        #if oldstyle:
        #    print "new theme", (cnew.red, cnew.green, cnew.blue), (cold.red, cold.green, cold.blue)
        #else: print "new theme", (cnew.red, cnew.green, cnew.blue)

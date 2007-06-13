import gtk, cairo
from os import path, mkdir
from pychess.Utils.const import prefix
from array import array

class Background (gtk.DrawingArea):
    
    def __init__ (self):
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.expose)
        self.connect("style-set", self.newtheme)
        self.clearpath = prefix("glade/clear.png")
        self.surface = None
    
    def expose (self, widget, event):
        cr = widget.window.cairo_create()
        cr.rectangle (event.area.x, event.area.y, event.area.width, event.area.height)
        if not self.surface:
            self.newtheme(self, self.get_style())
        cr.set_source_surface(self.surface, 0, 0)
        pattern = cr.get_source()
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
        
        dark = array('B',map(lambda x: x/256, (dnew.red, dnew.green, dnew.blue)))
        
        pydir = path.expanduser("~/.pychess/")
        temppngdir = path.join(pydir,"temp.png")
        if not path.isdir(pydir):
            mkdir(pydir)
        if path.isfile(temppngdir):
            f = open(temppngdir)
            b,g,r = [ord(c) for c in f.read(3)]
            if dark[0] == r and dark[1] == g and dark[2] == b:
                self.surface = cairo.ImageSurface.create_from_png(f)
                return
        
        surface = cairo.ImageSurface.create_from_png(self.clearpath)
        if hasattr(surface, "get_data_as_rgba"):
            buffer = surface.get_data_as_rgba()
        else: buffer = surface.get_data()
        
        data = array ('B', 'a' * surface.get_width() * surface.get_height() * 4)
        surf = cairo.ImageSurface.create_for_data (data, cairo.FORMAT_ARGB32,
                surface.get_width(), surface.get_height(), surface.get_stride())
        ctx = cairo.Context (surf)
        ctx.rectangle (0, 0, surface.get_width(), surface.get_height())
        ctx.set_source_surface(surface, 0, 0)
        ctx.fill()
        
        dark.reverse()

        rang3 = range(3)
        for s in xrange(0, len(data), 4):
            for i in rang3:
                data[s+i] = (dark[i] + data[s+i]) /3
        
        self.surface = cairo.ImageSurface.create_for_data (
            data, cairo.FORMAT_ARGB32,
            surface.get_width(), surface.get_height(),
            surface.get_stride())
        
        f = open(temppngdir, "w")
        for color in dark:
            f.write(chr(color))
        self.surface.write_to_png(f)

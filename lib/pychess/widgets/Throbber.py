import sys
import time
import math

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
import cairo

if sys.platform == 'win32':
    from pychess.System.WinRsvg import rsvg
else:    
    from gi.repository import Rsvg
    
from pychess.System.uistuff import addDataPrefix
from pychess.System.repeat import repeat_sleep
from pychess.System import glock

MAX_FPS = 20
RAD_PS = 2*math.pi

class Throbber (Gtk.DrawingArea):
    def __init__(self, width, height):       
        GObject.GObject.__init__(self)        
        self.connect("draw", self.__expose)
        self.surface = self.__loadSvg(addDataPrefix("glade/throbber.svg"),
                                      width, height)
        self.width = width
        self.height = height
        self.started = False
        self.stopped = False
        repeat_sleep(self.redraw, 1./MAX_FPS)
    
    def __expose(self, widget, context):
        #context = widget.window.cairo_create()
        
        if not self.started:
            self.started = time.time()
        ds = time.time() - self.started
        r = -RAD_PS * ds
        
        matrix = cairo.Matrix()
        matrix.translate(self.width/2, self.height/2)
        matrix.rotate(int(r/(2*math.pi)*12)/12.*2*math.pi)
        matrix.translate(-self.width/2, -self.height/2)
        context.transform(matrix)
        
        context.set_source_surface(self.surface, 0, 0)
        context.paint()
    
    def redraw (self):
        if self.stopped:
            return False
        
        window = self.get_window()        
        if window:
            glock.acquire()
            try:
                window = self.get_window()                
                if window:
                    a = self.get_allocation()
                    rect = Gdk.Rectangle()
                    rect.x, rect.y, rect.width, rect.height = (0, 0, a.width, a.height)
                    self.get_window().invalidate_rect(rect, True)
                    self.get_window().process_updates(True)
                    return True
            finally:
                glock.release()

    def stop (self):    
        self.stopped = True
        
    def __loadSvg (self, path, width, height):                         
        svg = Rsvg.Handle.new_from_file(path)       
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)       
        context = cairo.Context(surface)       
        context.set_operator(cairo.OPERATOR_SOURCE)        
        if svg.props.width != width or svg.props.height != height:
            context.scale(width/float(svg.props.width),
                          height/float(svg.props.height))        
        svg.render_cairo(context)
        return surface

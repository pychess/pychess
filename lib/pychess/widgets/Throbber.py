import time
import math

import gtk
import gobject
import cairo
import rsvg

from pychess.System.uistuff import addDataPrefix
from pychess.System.repeat import repeat_sleep
from pychess.System import glock

MAX_FPS = 20
RAD_PS = 2*math.pi

class Throbber (gtk.DrawingArea):
    def __init__(self, width, height):
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.__expose)
        self.surface = self.__loadSvg(addDataPrefix("glade/throbber.svg"),
                                      width, height)
        self.width = width
        self.height = height
        self.started = False
        repeat_sleep(self.redraw, 1./MAX_FPS)
    
    def __expose(self, widget, event):
        context = widget.window.cairo_create()
        
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
        if self.window:
            glock.acquire()
            try:
                if self.window:
                    a = self.get_allocation()
                    rect = gtk.gdk.Rectangle(0, 0, a.width, a.height)
                    self.window.invalidate_rect(rect, True)
                    self.window.process_updates(True)
                    return True
            finally:
                glock.release()
    
    def __loadSvg (self, path, width, height):
        svg = rsvg.Handle(path)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        context = cairo.Context(surface)
        context.set_operator(cairo.OPERATOR_SOURCE)
        if svg.props.width != width or svg.props.height != height:
            context.scale(width/float(svg.props.width),
                          height/float(svg.props.height))
        svg.render_cairo(context)
        return surface

import cairo

from gi.repository import Gtk

from math import ceil as fceil
ceil = lambda f: int(fceil(f))

from __init__ import NORTH, EAST, SOUTH, WEST, CENTER
from OverlayWindow import OverlayWindow

class HighlightArea (OverlayWindow):
    """ An entirely blue widget """
    
    def __init__ (self, parent):
        OverlayWindow.__init__(self, parent)
        self.myparent = parent       
        self.connect_after("draw", self.__onExpose)
    
    def showAt (self, position):
        alloc = self.myparent.get_allocation()
        if position == NORTH:
            x, y = 0, 0
            width, height = alloc.width, alloc.height*0.381966011
        elif position == EAST:
            x, y = alloc.width*0.618033989, 0
            width, height = alloc.width*0.381966011, alloc.height
        elif position == SOUTH:
            x, y = 0, alloc.height*0.618033989
            width, height = alloc.width, alloc.height*0.381966011
        elif position == WEST:
            x, y = 0, 0
            width, height = alloc.width*0.381966011, alloc.height
        elif position == CENTER:
            x, y = 0, 0
            width, height = alloc.width, alloc.height
        
        x, y = self.translateCoords(int(x), int(y))
        self.move(x, y)
        self.resize(ceil(width), ceil(height))
        self.show()
        
    def __onExpose (self, self_, ctx):
        context = self.get_window().cairo_create()
        a = self_.get_allocation()
        context.rectangle(a.x, a.y, a.width, a.height)        
        if self.is_composited():
            # FIXME
            #color = self.get_style().light[Gtk.StateType.SELECTED]
            sc = self.get_style_context()
            found, color = sc.lookup_color('p_light_color')
            context.set_operator(cairo.OPERATOR_CLEAR)
            context.set_source_rgba(0,0,0,0.0)
            context.fill_preserve ()
            context.set_operator(cairo.OPERATOR_OVER)
            context.set_source_rgba(color.red/65535., color.green/65535., color.blue/65535., 0.5)
            context.fill()
        else:
            context.set_source_color(self.get_style().light[Gtk.StateType.SELECTED])
            context.set_operator(cairo.OPERATOR_OVER)
            context.fill()

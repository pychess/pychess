import gtk

from math import ceil as fceil
ceil = lambda f: int(fceil(f))

from __init__ import NORTH, EAST, SOUTH, WEST, CENTER

class HighlightArea (gtk.DrawingArea):
    """ An entirely blue widget """
    
    def __init__ (self):
        gtk.DrawingArea.__init__(self)
        self.connect_after("expose-event", self.__onExpose)
    
    def showAt (self, position):
        alloc = self.get_parent().get_allocation()
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
        
        self.set_size_request(ceil(width), ceil(height))
        self.get_parent().move(self, int(x), int(y))
        self.show()
    
    def __onExpose (self, self_, event):
        context = self.window.cairo_create()
        context.set_source_color(self.get_style().light[gtk.STATE_SELECTED])
        context.rectangle(event.area)
        context.fill()

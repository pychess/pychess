
import gtk, gtk.gdk, cairo
from gobject import *
import math

line = 10
curve = 60
dotSmall = 12
dotLarge = 20

class SpotGraph (gtk.DrawingArea):
    
    __gsignals__ = {
        'spot_clicked' : (SIGNAL_RUN_FIRST, TYPE_NONE, (int,))
    }
    
    def __init__ (self):
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.expose)
        
        self.typeColors = [[[85, 152, 215], [59, 106, 151]],
                           [[115, 210, 22], [78, 154, 6]]]
        for type in self.typeColors:
            for color in type:
                color[0] = color[0]/255.
                color[1] = color[1]/255.
                color[2] = color[2]/255.
        
        #self.connect("button_press_event", self.button_press)
        #self.connect("button_release_event", self.button_release)
        #self.add_events(gtk.gdk.LEAVE_NOTIFY_MASK|gtk.gdk.POINTER_MOTION_MASK)
        #self.connect("motion_notify_event", self.motion_notify)
        #self.connect("leave_notify_event", self.leave_notify)
        
        self.spots = {}
        
    def redraw_canvas(self, rect=None):
        if self.window:
            if not rect:
                alloc = self.get_allocation()
                rect = (0, 0, alloc.width, alloc.height)
            rect = gtk.gdk.Rectangle(*map(int,rect))
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)
    
    def expose(self, widget, event):
        context = widget.window.cairo_create()
        self.draw(context, event.area)
        return False
    
    def draw (self, context, r):
        alloc = self.get_allocation()
        width = alloc.width
        height = alloc.height
        
        context.move_to(line, line)
        context.rel_line_to(0, height-line*2-curve)
        context.rel_curve_to(0, curve,  0, curve,  curve, curve)
        context.rel_line_to(width-line*2-curve, 0)
        
        context.set_line_width(line)
        context.set_line_cap(cairo.LINE_CAP_ROUND)
        context.set_source_color(self.get_style().dark[gtk.STATE_ACTIVE])
        context.stroke()
        
        context.set_line_width(dotSmall)
        for x, y, type in self.spots.values():
            context.new_path()
            context.set_source_rgb(*self.typeColors[type][0])
            x = x*(width-line)+line
            y = y*(height-line)-line
            context.arc(x, y, dotSmall/2., 0, 2 * math.pi)
            context.fill_preserve()
            context.set_line_width(dotSmall/10.)
            context.set_source_rgb(*self.typeColors[type][1])
            context.stroke()
        
    def addSpot (self, name, x0, y0, type=0):
        """ x and y are in % from 0 to 1 """
        assert type in range(len(self.typeColors))
        x1, y1 = self.getNearestFreeNeighbour(x0, 1-y0)
        self.spots[name] = (x1, y1, type)
        self.redraw_canvas(self.getBounds(x1, y1))
    
    def removeSpot (self, name):
        if not name in self.spots:
            return
        x, y, type = self.spots.pop(name)
        self.redraw_canvas(self.getBounds(x,y))
    
    def clearSpots (self):
        self.spots = {}
        self.redraw_canvas()
        self.redraw_canvas()
    
    def getBounds (self, x, y):
        alloc = self.get_allocation()
        width = alloc.width
        height = alloc.height
        
        x = x*(width-line)+line
        y = y*(height-line)-line
        
        return (x-dotSmall/2-1, y-dotSmall/2-1, x+dotSmall/2+1, y+dotSmall/2+1)
    
    def getNearestFreeNeighbour (self, xorg, yorg):
        
        """ This method performs a spircal search for an empty square to put a
            new dot. """
        
        # FIXME: This spiral search is squared, which means it it not very
        # suitable for circles
         
        #  49 26 27 28 29 30 31
        #  48 25  9 10 11 12 32
        #  47 24  8  1  2 13 33
        #  46 23  7  X  3 14 34
        #  45 22  6  5  4 15 35
        #  44 21 20 18 17 16 36
        #  43 42 41 40 39 38 37
        
        up = 1
        right = 1
        down = 2
        left = 2
        
        # To search, we have to translate points for % to px
        alloc = self.get_allocation()
        width = float(alloc.width)
        height = float(alloc.height)
        
        x = xorg * width
        y = yorg * height
        
        # Start by testing current spot
        if self.isEmpty (x, y):
            return x/width, y/height
        
        while True:

            for i in range(up):
                y -= dotSmall
                if self.isEmpty (x, y):
                    return x/width, y/height

            for i in range(right):
                x += dotSmall
                if self.isEmpty (x, y):
                    return x/width, y/height

            for i in range(down):
                y += dotSmall
                if self.isEmpty (x, y):
                    return x/width, y/height

            for i in range(left):
                x -= dotSmall
                if self.isEmpty (x, y):
                    return x/width, y/height
            
            # Grow spiral bounds
            right += 2
            down += 2
            left += 2
            up += 2
        
    def isEmpty (self, x0, y0):
        
        # Make sure spiral search don't put dots outside the graph
        alloc = self.get_allocation()
        width = alloc.width
        height = alloc.height
        if not 0 <= x0 <= width or not 0 <= y0 <= height:
            return False
        
        for x1, y1, type in self.spots.values():
            x1 = x1*width
            y1 = y1*height
            if (x1-x0)**2 + (y1-y0)**2 <= dotSmall**2:
                return False
        
        return True

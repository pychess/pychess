import math
ceil = lambda f: int(math.ceil(f))

from gobject import *
import gtk
import cairo
import pango

from pychess.System.uistuff import tooltip, tooltipStyle

line = 10
curve = 60
dotSmall = 14
dotLarge = 24
lineprc = 1/7.

hpadding = 5
vpadding = 3

class SpotGraph (gtk.EventBox):
    
    __gsignals__ = {
        'spotClicked' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,))
    }
    
    def __init__ (self):
        gtk.EventBox.__init__(self)
        self.connect("expose_event", self.expose)
        
        self.typeColors = [[[85, 152, 215], [59, 106, 151]],
                           [[115, 210, 22], [78, 154, 6]]]
        for type in self.typeColors:
            for color in type:
                color[0] = color[0]/255.
                color[1] = color[1]/255.
                color[2] = color[2]/255.
        
        self.add_events( gtk.gdk.LEAVE_NOTIFY_MASK |
                         gtk.gdk.POINTER_MOTION_MASK |
                         gtk.gdk.BUTTON_PRESS_MASK |
                         gtk.gdk.BUTTON_RELEASE_MASK )
        
        self.connect("button_press_event", self.button_press)
        self.connect("button_release_event", self.button_release)
        self.connect("motion_notify_event", self.motion_notify)
        self.connect("leave_notify_event", self.motion_notify)
        self.connect("size-allocate", self.size_allocate)
        
        self.cords = []
        self.hovered = None
        self.pressed = False
        self.spots = {}
        self.spotQueue = [] # For spots added prior to widget allocation
        
        self.xmarks = []
        self.ymarks = []
        self.set_visible_window(False)
    
    ############################################################################
    # Drawing                                                                  #
    ############################################################################
    
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
        
        #------------------------------------------------------ Paint side ruler
        context.move_to(alloc.x+line, alloc.y+line)
        context.rel_line_to(0, height-line*2-curve)
        context.rel_curve_to(0, curve,  0, curve,  curve, curve)
        context.rel_line_to(width-line*2-curve, 0)
        
        context.set_line_width(line)
        context.set_line_cap(cairo.LINE_CAP_ROUND)
        state = self.state == gtk.STATE_NORMAL and gtk.STATE_PRELIGHT or self.state
        context.set_source_color(self.get_style().dark[state])
        context.stroke()
        
        #------------------------------------------------ Paint horizontal marks
        for x, title in self.xmarks:
            context.set_source_color(self.get_style().fg[self.state])
            context.set_font_size(12)
            x, y = self.prcToPix (x, 1)
            context.move_to (x+line/2., y-line/2.)
            context.rotate(-math.pi/2)
            context.show_text(title)
            context.rotate(math.pi/2)
            
            context.set_source_color(self.get_style().bg[self.state])
            context.move_to (x-line/2., y)
            context.rel_curve_to (6, 0,  6, line,  6, line)
            context.rel_curve_to (0, -line,  6, -line,  6, -line)
            context.close_path()
            context.fill()
        
        #-------------------------------------------------- Paint vertical marks
        for y, title in self.ymarks:
            context.set_source_color(self.get_style().fg[self.state])
            context.set_font_size(12)
            x, y = self.prcToPix (0, y)
            context.move_to (x+line/2., y+line/2.)
            context.show_text(title)
            
            context.set_source_color(self.get_style().bg[self.state])
            context.move_to (x, y-line/2.)
            context.rel_curve_to (0, 6,  -line, 6,  -line, 6)
            context.rel_curve_to (line, 0,  line, 6,  line, 6)
            context.close_path()
            context.fill()
        
        #----------------------------------------------------------- Paint spots
        context.set_line_width(dotSmall*lineprc)
        for x, y, type, name, text in self.spots.values():
            context.set_source_rgb(*self.typeColors[type][0])
            if self.hovered and name == self.hovered[3]:
                continue
            
            x, y = self.prcToPix (x, y)
            context.arc(x, y, dotSmall/(1+lineprc)/2., 0, 2 * math.pi)
            context.fill_preserve()
            context.set_source_rgb(*self.typeColors[type][1])
            context.stroke()
        
        #--------------------------------------------------- Paint hovered spots
        context.set_line_width(dotLarge*lineprc)
        if self.hovered:
            x, y, type, name, text = self.hovered
            x, y = self.prcToPix (x, y)
            if not self.pressed:
                context.set_source_rgb(*self.typeColors[type][0])
            else:
                context.set_source_rgb(*self.typeColors[type][1])
            context.arc(x, y, dotLarge/(1+lineprc)/2., 0, 2 * math.pi)
            context.fill_preserve()
            context.set_source_rgb(*self.typeColors[type][1])
            context.stroke()
            
            x, y, width, height = self.getTextBounds(self.hovered)
            
            oldstyle = self.get_style()
            self.set_style(tooltipStyle)
            tooltipStyle.paint_flat_box (self.window,
                gtk.STATE_NORMAL, gtk.SHADOW_NONE, None, tooltip, "tooltip",
                int(x-hpadding), int(y-vpadding),
                ceil(width+hpadding*2), ceil(height+vpadding*2))
            self.set_style(oldstyle)
            
            context.move_to(x, y)
            context.set_source_color(tooltipStyle.fg[self.state])
            context.show_layout(self.create_pango_layout(text))
    
    ############################################################################
    # Events                                                                   #
    ############################################################################
    
    def button_press (self, widget, event):
        alloc = self.get_allocation()
        self.cords = [event.x+alloc.x, event.y+alloc.y]
        self.pressed = True
        if self.hovered:
            self.redraw_canvas(self.getBounds(self.hovered))
    
    def button_release (self, widget, event):
        alloc = self.get_allocation()
        self.cords = [event.x+alloc.x, event.y+alloc.y]
        self.pressed = False
        if self.hovered:
            self.redraw_canvas(self.getBounds(self.hovered))
            if self.pointIsOnSpot (event.x+alloc.x, event.y+alloc.y, self.hovered):
                self.emit("spotClicked", self.hovered[3])
    
    def motion_notify (self, widget, event):
        alloc = self.get_allocation()
        self.cords = [event.x+alloc.x, event.y+alloc.y]
        spot = self.getSpotAtPoint (*self.cords)
        if self.hovered and spot == self.hovered:
            return
        if self.hovered:
            bounds = self.getBounds(self.hovered)
            self.hovered = None
            self.redraw_canvas(bounds)
        if spot:
            self.hovered = spot
            self.redraw_canvas(self.getBounds(self.hovered))
    
    def size_allocate (self, widget, allocation):
        assert self.get_allocation().width > 1
        for spot in self.spotQueue:
            self.addSpot(*spot)
        del self.spotQueue[:]
    
    ############################################################################
    # Interaction                                                              #
    ############################################################################
    
    def addSpot (self, name, text, x0, y0, type=0):
        """ x and y are in % from 0 to 1 """
        assert type in range(len(self.typeColors))
        
        if self.get_allocation().width <= 1:
            self.spotQueue.append((name, text, x0, y0, type))
            return
        
        x1, y1 = self.getNearestFreeNeighbourHexigon(x0, 1-y0)
        spot = (x1, y1, type, name, text)
        self.spots[name] = spot
        if not self.hovered and self.cords and \
                self.pointIsOnSpot (self.cords[0], self.cords[1], spot):
            self.hovered = spot
        self.redraw_canvas(self.getBounds(spot))
    
    def removeSpot (self, name):
        if not name in self.spots:
            return
        spot = self.spots.pop(name)
        bounds = self.getBounds(spot)
        if spot == self.hovered:
            self.hovered = None
        self.redraw_canvas(bounds)
    
    def clearSpots (self):
        self.hovered = None
        self.spots.clear()
        self.redraw_canvas()
        self.redraw_canvas()
    
    def addXMark (self, x, title):
        self.xmarks.append( (x, title) )
    
    def addYMark (self, y, title):
        self.ymarks.append( (1-y, title) )
    
    ############################################################################
    # Internal stuff                                                           #
    ############################################################################
    
    def getTextBounds (self, spot):
        x, y, type, name, text = spot
        x, y = self.prcToPix (x, y)
        
        alloc = self.get_allocation()
        width = alloc.width
        height = alloc.height
        
        extends = self.create_pango_layout(text).get_extents()
        scale = float(pango.SCALE)
        x_bearing, y_bearing, twidth, theight = [e/scale for e in extends[1]]
        tx = x - x_bearing + dotLarge/2.
        ty = y - y_bearing - theight - dotLarge/2.
        
        if tx + twidth > width and x - x_bearing - twidth - dotLarge/2. > alloc.x:
            tx = x - x_bearing - twidth - dotLarge/2.
        if ty < alloc.y:
            ty = y - y_bearing + dotLarge/2.
        
        return (tx, ty, twidth, theight)
    
    def join (self, r0, r1):
        x1 = min(r0[0], r1[0])
        x2 = max(r0[0]+r0[2], r1[0]+r1[2])
        y1 = min(r0[1], r1[1])
        y2 = max(r0[1]+r0[3], r1[1]+r1[3])
        return (x1, y1, x2 - x1, y2 - y1)
    
    def getBounds (self, spot):
        
        x, y, type, name, text = spot
        x, y = self.prcToPix (x, y)
        
        if spot == self.hovered:
            size = dotLarge
        else: size = dotSmall
        
        bounds = (x-size/2.-1, y-size/2.-1, size+2, size+2)
        
        if spot == self.hovered:
            x, y, w, h = self.getTextBounds(spot)
            tbounds = (x-hpadding, y-vpadding, w+hpadding*2+1, h+vpadding*2+1)
            return self.join(bounds, tbounds)
        
        return bounds
    
    def getNearestFreeNeighbourHexigon (self, xorg, yorg):
        """ This method performs an hexigon search for an empty place to put a
            new dot. """
        
        x, y = self.prcToPix (xorg, yorg)
        # Start by testing current spot
        if self.isEmpty (x, y):
            return xorg, yorg
        
        directions = [(math.cos((i+2)*math.pi/3),
                       math.sin((i+2)*math.pi/3)) for i in xrange(6)]
        
        level = 1
        while True:
            x += dotSmall
            for dx, dy in directions:
                for i in xrange(level):
                    if self.isEmpty (x, y):
                        return self.pixToPrc (x, y)
                    x += dx*dotSmall
                    y += dy*dotSmall
            level += 1
    
    def getNearestFreeNeighbourArchi (self, xorg, yorg):
        """ This method performs an archimedes-spircal search for an empty
            place to put a new dot.
            http://en.wikipedia.org/wiki/Archimedean_spiral """
        
        xorg, yorg = self.prcToPix (xorg, yorg)
        # Start by testing current spot
        if self.isEmpty (xorg, yorg):
            return self.pixToPrc (xorg, yorg)
        
        r = 0
        while True:
            # This is an approx to the equation
            # cos((r-s)/(2pi)) = (r^2+s^2-1)/(2*r*s)
            # which gives the next point on the spiral 1 away.
            r = (4*math.pi**3*r + r**2 + math.sqrt(16*math.pi**6 +
                 8*math.pi**3*r + r**4)) / (4*math.pi**3 + 2*r)
            
            x = r*math.cos(r)/(4*math.pi)*dotSmall + xorg
            y = r*math.sin(r)/(4*math.pi)*dotSmall + yorg
            if self.isEmpty (x, y):
                return self.pixToPrc (x, y)
    
    def getNearestFreeNeighbourSquare (self, xorg, yorg):
        
        """ This method performs a spircal search for an empty square to put a
            new dot. """
        
        up = 2
        right = 1
        down = 1
        left = 2
        
        x, y = self.prcToPix (xorg, yorg)
        
        # Start by testing current spot
        if self.isEmpty (x, y):
            return self.pixToPrc (x, y)
        
        while True:

            for i in range(right):
                x += dotSmall
                if self.isEmpty (x, y):
                    return self.pixToPrc (x, y)

            for i in range(down):
                y += dotSmall
                if self.isEmpty (x, y):
                    return self.pixToPrc (x, y)

            for i in range(left):
                x -= dotSmall
                if self.isEmpty (x, y):
                    return self.pixToPrc (x, y)
            
            for i in range(up):
                y -= dotSmall
                if self.isEmpty (x, y):
                    return self.pixToPrc (x, y)
            
            # Grow spiral bounds
            right += 2
            down += 2
            left += 2
            up += 2
    
    def isEmpty (self, x0, y0):
        """ Returns true if a spot placed on (x, y) is inside the graph and not
            intersecting with other spots.
            x and y should be in pixels, not percent """
        
        # Make sure spiral search don't put dots outside the graph
        x, y = self.prcToPix(0,0)
        w, h = self.prcToPix(1,1)
        
        if not x <= x0 <= w or not y <= y0 <= h:
            return False
        
        # Tests if the spot intersects any other spots
        for x1, y1, type, name, text in self.spots.values():
            x1, y1 = self.prcToPix(x1, y1)
            if (x1-x0)**2 + (y1-y0)**2 < dotSmall**2 - 0.1:
                return False
        
        return True
    
    def pointIsOnSpot (self, x0, y0, spot):
        """ Returns true if (x, y) is inside the spot 'spot'. The size of the
            spot is determined based on its hoverness.
            x and y should be in pixels, not percent """
        
        if spot == self.hovered:
            size = dotLarge
        else: size = dotSmall
        
        x1, y1, type, name, text = spot
        x1, y1 = self.prcToPix(x1, y1)
        if (x1-x0)**2 + (y1-y0)**2 <= (size/2.)**2:
            return True
        return False
    
    def getSpotAtPoint (self, x, y):
        """ Returns the spot embrace (x, y) if any. Otherwise it returns None.
            x and y should be in pixels, not percent """
        
        if self.hovered and self.pointIsOnSpot(x, y, self.hovered):
            return self.hovered
        
        for spot in self.spots.values():
            if spot == self.hovered:
                continue
            if self.pointIsOnSpot(x, y, spot):
                return spot
        
        return None
    
    def prcToPix (self, x, y):
        """ Translates from 0-1 cords to real world cords """ 
        alloc = self.get_allocation()
        return x*(alloc.width - line*1.5-dotLarge*0.5) + line*1.5 + alloc.x, \
               y*(alloc.height - line*1.5-dotLarge*0.5) + dotLarge*0.5 + alloc.y
    
    def pixToPrc (self, x, y):
        """ Translates from real world cords to 0-1 cords """ 
        alloc = self.get_allocation()
        return (x - line*1.5 - alloc.x)/(alloc.width - line*1.5-dotLarge*0.5), \
               (y - dotLarge*0.5 - alloc.y)/(alloc.height - line*1.5-dotLarge*0.5)

if __name__ == "__main__":
    w = gtk.Window()
    nb = gtk.Notebook()
    w.add(nb)
    vb = gtk.VBox()
    nb.append_page(vb)
    
    sg = SpotGraph()
    sg.addXMark(.5, "Center")
    sg.addYMark(.5, "Center")
    vb.pack_start(sg)
    
    button = gtk.Button("New Spot")
    def callback (button):
        if not hasattr(button, "nextnum"):
            button.nextnum = 0
        else: button.nextnum += 1
        sg.addSpot(str(button.nextnum), "Blablabla", 1, 1, 0)
    button.connect("clicked", callback) 
    vb.pack_start(button, expand=False)
    
    w.connect("delete-event", gtk.main_quit)
    w.show_all()
    w.resize(400,400)
    gtk.main()

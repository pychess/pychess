from math import ceil as float_ceil
ceil = lambda f: int(float_ceil(f))

import gtk
import gobject

from AbstractArrowButton import AbstractArrowButton

POSITIONS_COUNT = 5
NORTH, EAST, SOUTH, WEST, CENTER = range(POSITIONS_COUNT)
DX_DY = ((0,-1), (1,0), (0,1), (-1,0), (0,0))
PADDING_X = 0.2 # Amount of button width
PADDING_Y = 0.4 # Amount of button height

class StarArrowButton (AbstractArrowButton):
    
    __gsignals__ = {
        'dropped' : (gobject.SIGNAL_RUN_FIRST, None, (int, object)),
        'hovered' : (gobject.SIGNAL_RUN_FIRST, None, (int, object)),
        'left' : (gobject.SIGNAL_RUN_FIRST, None, ()),
    }
    
    def __init__ (self, northSvg, eastSvg, southSvg, westSvg, centerSvg, bgSvg):
        AbstractArrowButton.__init__(self)
        
        self.svgs = (northSvg, eastSvg, southSvg, westSvg, centerSvg)
        self.bgSvg = bgSvg
        self.size = ()
        self.connect("expose-event", self.__onExposeEvent)
        self.currentHovered = -1
        
        targets = [("GTK_NOTEBOOK_TAB", gtk.TARGET_SAME_APP, 0xbadbeef)]
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                           targets, gtk.gdk.ACTION_MOVE)
        self.drag_dest_set_track_motion(True)
        self.connect("drag-motion", self.__onDragMotion)
        self.connect("drag-leave", self.__onDragLeave)
        self.connect("drag-drop", self.__onDragDrop)
        
        self.parentAlloc = None
        self.size = ()
    
    def __calcSize (self):
        parentAlloc = self.get_parent().get_allocation()
        if self.parentAlloc != None and \
                parentAlloc.x == self.parentAlloc.x and \
                parentAlloc.y == self.parentAlloc.y and \
                parentAlloc.width == self.parentAlloc.width and \
                parentAlloc.height == self.parentAlloc.height:
            return
        self.parentAlloc = parentAlloc
        
        starWidth, starHeight = self.getSizeOfSvg(self.bgSvg)
        scale = min(1,
                    parentAlloc.width  / float(starWidth),
                    parentAlloc.height / float(starHeight))
        
        self.size = map(int, (starWidth*scale, starHeight*scale))
        self.set_size_request(self.size[0], self.size[1])
        
        self.get_parent().move(self,
                               int(parentAlloc.width/2. - self.size[0]/2.),
                               int(parentAlloc.height/2. - self.size[1]/2.))
    
    def __onExposeEvent (self, self_, event):
        self.__calcSize()
        #self.window.set_composited(True)
        #print gtk.gdk.display_get_default().supports_cursor_alpha()
        
        context = self.window.cairo_create()
        surface = self.getSurfaceFromSvg(self.bgSvg, self.size[0], self.size[1])
        context.set_source_surface(surface, 0, 0)
        context.paint()
        
        for position in range(POSITIONS_COUNT):
            rect = self.__getButtonRectangle(position)
            
            context = self.window.cairo_create()
            surface = self.getSurfaceFromSvg(self.svgs[position],
                                             rect.width, rect.height)
            context.set_source_surface(surface, rect.x, rect.y)
            context.paint()
    
    def __getButtonRectangle (self, position):
        starWidth, starHeight = self.getSizeOfSvg(self.bgSvg)
        buttonWidth, buttonHeight = self.getSizeOfSvg(self.svgs[position])
        
        buttonWidth = buttonWidth * self.size[0]/float(starWidth)
        buttonHeight = buttonHeight * self.size[1]/float(starHeight)
        dx, dy = DX_DY[position] 
        x = ceil(dx*(1+PADDING_X)*buttonWidth - buttonWidth/2. + self.size[0]/2.)
        y = ceil(dy*(1+PADDING_Y)*buttonHeight - buttonHeight/2. + self.size[1]/2.)
        
        return gtk.gdk.Rectangle(x, y, ceil(buttonWidth), ceil(buttonHeight))
    
    def __getButtonAtPoint (self, x, y):
        for position in xrange(POSITIONS_COUNT):
            region = gtk.gdk.region_rectangle(self.__getButtonRectangle(position))
            if region.point_in(x, y):
                return position
        return -1
    
    def __onDragMotion (self, arrow, context, x, y, timestamp):
        position = self.__getButtonAtPoint(x, y)
        if self.currentHovered != position:
            self.currentHovered = position
            if position > -1:
                self.emit("hovered", position, context.get_source_widget())
            else: self.emit("left")
        
        if position > -1:
            context.drag_status (gtk.gdk.ACTION_MOVE, timestamp)
            return True
        context.drag_status (gtk.gdk.ACTION_DEFAULT, timestamp)
    
    def __onDragLeave (self, arrow, context, timestamp):
        if self.currentHovered != -1:
            self.currentHovered = -1
            self.emit("left")
    
    def __onDragDrop (self, arrow, context, x, y, timestamp):
        position = self.__getButtonAtPoint(x, y)
        if position > -1:
            self.emit("dropped", position, context.get_source_widget())
            context.finish(True, True, timestamp)
            return True

if __name__ == "__main__":
    w = gtk.Window()
    w.connect("delete-event", gtk.main_quit)
    hbox = gtk.HBox()
    
    l = gtk.Layout()
    l.set_size_request(200,200)
    sab = StarArrowButton("/home/thomas/Programmering/workspace/pychess/glade/dock_top.svg",
                          "/home/thomas/Programmering/workspace/pychess/glade/dock_right.svg",
                          "/home/thomas/Programmering/workspace/pychess/glade/dock_bottom.svg",
                          "/home/thomas/Programmering/workspace/pychess/glade/dock_left.svg",
                          "/home/thomas/Programmering/workspace/pychess/glade/dock_center.svg",
                          "/home/thomas/Programmering/workspace/pychess/glade/dock_star.svg")
    sab.set_size_request(200,200)
    l.put(sab, 0, 0)
    hbox.add(l)
    def handle (*args):
        sab.showAt(l, CENTER)
    l.connect("button-press-event", handle)
    
    nb = gtk.Notebook()
    label = gtk.Label("hi")
    nb.append_page(label)
    nb.set_tab_detachable(label, True)
    hbox.add(nb)
    w.add(hbox)
    w.show_all()
    gtk.main()

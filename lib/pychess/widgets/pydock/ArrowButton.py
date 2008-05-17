import gtk
import gobject

from AbstractArrowButton import AbstractArrowButton

from __init__ import NORTH, EAST, SOUTH, WEST

class ArrowButton (AbstractArrowButton):
    """ Leafs will connect to the drag-drop signal """
    
    __gsignals__ = {
        'dropped' : (gobject.SIGNAL_RUN_FIRST, None, (object,)),
        'hovered' : (gobject.SIGNAL_RUN_FIRST, None, (object,)),
        'left' : (gobject.SIGNAL_RUN_FIRST, None, ()),
    }
    
    def __init__ (self, svgPath, position):
        AbstractArrowButton.__init__(self)
        self.position = position
        self.svgPath = svgPath
        self.connect("expose-event", self.__onExposeEvent)
        self.parentAlloc = None
        
        targets = [("GTK_NOTEBOOK_TAB", gtk.TARGET_SAME_APP, 0xbadbeef)]
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                           targets, gtk.gdk.ACTION_MOVE)
        self.drag_dest_set_track_motion(True)
        self.connect("drag-motion", self.__onDragMotion)
        self.connect("drag-leave", self.__onDragLeave)
        self.connect("drag-drop", self.__onDragDrop)
        
        self.hovered = False
    
    def __calcSize (self):
        parentAlloc = self.get_parent().get_allocation()
        if self.parentAlloc != None and \
                parentAlloc.x == self.parentAlloc.x and \
                parentAlloc.y == self.parentAlloc.y and \
                parentAlloc.width == self.parentAlloc.width and \
                parentAlloc.height == self.parentAlloc.height:
            return
        self.parentAlloc = parentAlloc
        
        width, height = self.getSizeOfSvg(self.svgPath)
        self.set_size_request(width, height)
        
        if self.position == NORTH:
            x, y = parentAlloc.width/2.-width/2., 0
        elif self.position == EAST:
            x, y = parentAlloc.width-width, parentAlloc.height/2.-height/2.
        elif self.position == SOUTH:
            x, y = parentAlloc.width/2.-width/2., parentAlloc.height-height
        elif self.position == WEST:
            x, y = 0, parentAlloc.height/2.-height/2.
        
        self.get_parent().move(self, int(x), int(y))
    
    def __onExposeEvent (self, self_, event):
        self.__calcSize()
        
        context = self.window.cairo_create()
        width, height = self.getSizeOfSvg(self.svgPath)
        surface = self.getSurfaceFromSvg(self.svgPath, width, height)
        context.set_source_surface(surface, 0, 0)
        context.paint()
    
    def __containsPoint (self, x, y):
        alloc = self.get_allocation()
        return 0 <= x < alloc.width and 0 <= y < alloc.height
    
    def __onDragMotion (self, arrow, context, x, y, timestamp):
        if not self.hovered and self.__containsPoint(x,y):
            self.hovered = True
            self.emit("hovered", context.get_source_widget())
        elif self.hovered and not self.__containsPoint(x,y):
            self.hovered = False
            self.emit("left")
    
    def __onDragLeave (self, arrow, context, timestamp):
        if self.hovered:
            self.hovered = False
            self.emit("left")
    
    def __onDragDrop (self, arrow, context, x, y, timestamp):
        if self.__containsPoint(x,y):
            self.emit("dropped", context.get_source_widget())
            context.finish(True, True, timestamp)
            return True

from gi.repository import Gtk
from gi.repository import GObject
class BorderBox (Gtk.Alignment):
    def __init__ (self, widget=None, top=False, right=False,
                                     bottom=False, left=False):
        # FIXME
        #GObject.GObject.__init__(self, 0, 0, 1, 1)
        GObject.GObject.__init__(self)        
        self.connect("draw", self._onExpose)

        if widget:
            self.add(widget)
        
        self.__top = top
        self.__right = right
        self.__bottom = bottom
        self.__left = left
        self._updateBorders()
    
    
    def _onExpose(self, area, ctx):
        context = self.get_window().cairo_create()

        sc = self.get_style_context()
        found, color = sc.lookup_color("p_dark_color")
        context.set_source_rgba(*color)

        r = self.get_allocation()
        x = r.x + .5
        y = r.y + .5
        width = r.width - 1
        height = r.height - 1
        
        if self.top:
            context.move_to(x, y)
            context.line_to(x+width, y)
        if self.right:
            context.move_to(x+width, y)
            context.line_to(x+width, y+height)
        if self.bottom:
            context.move_to(x+width, y+height)
            context.line_to(x, y+height)
        if self.left:
            context.move_to(x, y+height)
            context.line_to(x, y)
        context.set_line_width(1)
        context.stroke()
    
    
    def _updateBorders (self):
        self.set_padding(self.top and 1 or 0,
                         self.bottom and 1 or 0,
                         self.right and 1 or 0,
                         self.left and 1 or 0)
    
    
    def isTop(self):
        return self.__top

    def isRight(self):
        return self.__right

    def isBottom(self):
        return self.__bottom

    def isLeft(self):
        return self.__left

    def setTop(self, value):
        self.__top = value
        self._updateBorders()

    def setRight(self, value):
        self.__right = value
        self._updateBorders()

    def setBottom(self, value):
        self.__bottom = value
        self._updateBorders()

    def setLeft(self, value):
        self.__left = value
        self._updateBorders()
    
    top = property(isTop, setTop, None, None)

    right = property(isRight, setRight, None, None)

    bottom = property(isBottom, setBottom, None, None)

    left = property(isLeft, setLeft, None, None)

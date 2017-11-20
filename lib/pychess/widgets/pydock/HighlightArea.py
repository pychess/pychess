
import cairo

from .__init__ import NORTH, EAST, SOUTH, WEST, CENTER
from .OverlayWindow import OverlayWindow

from math import ceil as fceil

# ceil = lambda f: int(fceil(f))


def ceil(f):
    return int(fceil(f))


class HighlightArea(OverlayWindow):
    """ An entirely blue widget """

    def __init__(self, parent):
        OverlayWindow.__init__(self, parent)
        self.cid = self.connect_after("draw", self.__onExpose)

    def showAt(self, position):
        alloc = self.myparent.get_allocation()
        if position == NORTH:
            x_loc, y_loc = 0, 0
            width, height = alloc.width, alloc.height * 0.381966011
        elif position == EAST:
            x_loc, y_loc = alloc.width * 0.618033989, 0
            width, height = alloc.width * 0.381966011, alloc.height
        elif position == SOUTH:
            x_loc, y_loc = 0, alloc.height * 0.618033989
            width, height = alloc.width, alloc.height * 0.381966011
        elif position == WEST:
            x_loc, y_loc = 0, 0
            width, height = alloc.width * 0.381966011, alloc.height
        elif position == CENTER:
            x_loc, y_loc = 0, 0
            width, height = alloc.width, alloc.height

        try:
            x_loc, y_loc = self.translateCoords(int(x_loc), int(y_loc))
            self.move(x_loc, y_loc)
        except ValueError:
            pass
            # Can't move to x,y, because top level parent has no window.

        self.resize(ceil(width), ceil(height))
        self.show()

    def __onExpose(self, self_, ctx):
        context = self.get_window().cairo_create()
        a = self_.get_allocation()
        context.rectangle(a.x, a.y, a.width, a.height)
        sc = self.get_style_context()
        found, color = sc.lookup_color('p_light_selected')
        if self.is_composited():
            context.set_operator(cairo.OPERATOR_CLEAR)
            context.set_source_rgba(0, 0, 0, 0.0)
            context.fill_preserve()
            context.set_operator(cairo.OPERATOR_OVER)
            context.set_source_rgba(color.red, color.green, color.blue, 0.5)
            context.fill()
        else:
            context.set_source_rgba(color.red, color.green, color.blue)
            context.set_operator(cairo.OPERATOR_OVER)
            context.fill()

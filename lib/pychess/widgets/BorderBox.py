from gi.repository import Gtk, GObject


class BorderBox(Gtk.Alignment):
    def __init__(self, widget=None, top=False, right=False, bottom=False, left=False):
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

        style_ctxt = self.get_style_context()
        color = style_ctxt.lookup_color("p_dark_color")[1]
        red, green, blue, alpha = color.red, color.green, color.blue, color.alpha
        context.set_source_rgba(red, green, blue, alpha)

        allocation = self.get_allocation()
        x_loc = allocation.x + 0.5
        y_loc = allocation.y + 0.5
        width = allocation.width - 1
        height = allocation.height - 1

        if self.top:
            context.move_to(x_loc, y_loc)
            context.line_to(x_loc + width, y_loc)
        if self.right:
            context.move_to(x_loc + width, y_loc)
            context.line_to(x_loc + width, y_loc + height)
        if self.bottom:
            context.move_to(x_loc + width, y_loc + height)
            context.line_to(x_loc, y_loc + height)
        if self.left:
            context.move_to(x_loc, y_loc + height)
            context.line_to(x_loc, y_loc)
        context.set_line_width(1)
        context.stroke()

    def _updateBorders(self):
        self.set_padding(
            self.top and 1 or 0,
            self.bottom and 1 or 0,
            self.right and 1 or 0,
            self.left and 1 or 0,
        )

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

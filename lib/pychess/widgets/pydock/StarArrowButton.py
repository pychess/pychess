from __future__ import absolute_import
from __future__ import print_function

from math import ceil as float_ceil, pi
import cairo

from gi.repository import Gtk, Gdk, GObject

from .OverlayWindow import OverlayWindow

# ceil = lambda f: int(float_ceil(f))


def ceil(num):
    return int(float_ceil(num))


POSITIONS_COUNT = 5
NORTH, EAST, SOUTH, WEST, CENTER = range(POSITIONS_COUNT)
DX_DY = ((0, -1), (1, 0), (0, 1), (-1, 0), (0, 0))
PADDING_X = 0.2  # Amount of button width
PADDING_Y = 0.4  # Amount of button height


class StarArrowButton(OverlayWindow):

    __gsignals__ = {
        'dropped': (GObject.SignalFlags.RUN_FIRST, None, (int, object)),
        'hovered': (GObject.SignalFlags.RUN_FIRST, None, (int, object)),
        'left': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, parent, northSvg, eastSvg, southSvg, westSvg, centerSvg,
                 bgSvg):
        OverlayWindow.__init__(self, parent)

        self.svgs = (northSvg, eastSvg, southSvg, westSvg, centerSvg)
        self.bgSvg = bgSvg
        self.size = ()
        self.currentHovered = -1

        # targets = [("GTK_NOTEBOOK_TAB", Gtk.TargetFlags.SAME_APP, 0xbadbeef)]
        targets = [Gtk.TargetEntry.new("GTK_NOTEBOOK_TAB",
                                       Gtk.TargetFlags.SAME_APP, 0xbadbeef)]
        self.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                           targets, Gdk.DragAction.MOVE)
        self.drag_dest_set_track_motion(True)
        self.myparent.button_cids += [
            self.connect("drag-motion", self.__onDragMotion),
            self.connect("drag-leave", self.__onDragLeave),
            self.connect("drag-drop", self.__onDragDrop),
            self.connect_after("draw", self.__onExposeEvent),
        ]
        self.myparentAlloc = None
        self.myparentPos = None
        self.hasHole = False
        self.size = ()

    def _calcSize(self):
        parentAlloc = self.myparent.get_allocation()

        if self.myparentAlloc is None or \
                parentAlloc.width != self.myparentAlloc.width or \
                parentAlloc.height != self.myparentAlloc.height:

            starWidth, starHeight = self.getSizeOfSvg(self.bgSvg)
            scale = min(1, parentAlloc.width / float(starWidth),
                        parentAlloc.height / float(starHeight))
            self.size = list(map(int, (starWidth * scale, starHeight * scale)))
            self.resize(self.size[0], self.size[1])

            if self.get_window():
                self.hasHole = True
                self.digAHole(self.bgSvg, self.size[0], self.size[1])

        elif not self.hasHole:
            self.hasHole = True
            self.digAHole(self.bgSvg, self.size[0], self.size[1])

        if self.myparent.get_window():
            x_loc, y_loc = self.translateCoords(
                int(parentAlloc.width / 2. - self.size[0] / 2.),
                int(parentAlloc.height / 2. - self.size[1] / 2.))
            if (x_loc, y_loc) != self.get_position():
                self.move(x_loc, y_loc)

            self.myparentPos = self.myparent.get_window().get_position()
        self.myparentAlloc = parentAlloc

    def __onExposeEvent(self, self_, ctx):
        self._calcSize()

        context = self.get_window().cairo_create()
        self.paintTransparent(context)
        surface = self.getSurfaceFromSvg(self.bgSvg, self.size[0],
                                         self.size[1])
        context.set_source_surface(surface, 0, 0)
        context.paint()

        for position in range(POSITIONS_COUNT):
            rect = self.__getButtonRectangle(position)

            context = self.get_window().cairo_create()
            surface = self.getSurfaceFromSvg(self.svgs[position], rect.width,
                                             rect.height)
            context.set_source_surface(surface, rect.x, rect.y)
            context.paint()

    def __getButtonRectangle(self, position):
        starWidth, starHeight = self.getSizeOfSvg(self.bgSvg)
        buttonWidth, buttonHeight = self.getSizeOfSvg(self.svgs[position])

        buttonWidth = buttonWidth * self.size[0] / float(starWidth)
        buttonHeight = buttonHeight * self.size[1] / float(starHeight)
        dx_loc, dy_loc = DX_DY[position]
        x_loc = ceil(dx_loc * (1 + PADDING_X) * buttonWidth - buttonWidth / 2. +
                     self.size[0] / 2.)
        y_loc = ceil(dy_loc * (1 + PADDING_Y) * buttonHeight - buttonHeight / 2. +
                     self.size[1] / 2.)

        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = (x_loc, y_loc, ceil(buttonWidth),
                                                   ceil(buttonHeight))
        return rect

    def __getButtonAtPoint(self, x, y):
        for position in range(POSITIONS_COUNT):

            rect = Gdk.Rectangle()
            rect.x, rect.y, rect.width, rect.height = (x, y, 1, 1)

            inside, dest = Gdk.rectangle_intersect(
                self.__getButtonRectangle(position), rect)
            if inside:
                return position
        return -1

    def __onDragMotion(self, arrow, context, x, y, timestamp):
        position = self.__getButtonAtPoint(x, y)
        if self.currentHovered != position:
            self.currentHovered = position
            if position > -1:
                self.emit("hovered", position,
                          Gtk.drag_get_source_widget(context))
            else:
                self.emit("left")

        if position > -1:
            Gdk.drag_status(context, Gdk.DragAction.MOVE, timestamp)
            return True
        Gdk.drag_status(context, Gdk.DragAction.DEFAULT, timestamp)

    def __onDragLeave(self, arrow, context, timestamp):
        if self.currentHovered != -1:
            self.currentHovered = -1
            self.emit("left")

    def __onDragDrop(self, arrow, context, x, y, timestamp):
        position = self.__getButtonAtPoint(x, y)
        if position > -1:
            self.emit("dropped", position, Gtk.drag_get_source_widget(context))
            context.finish(True, True, timestamp)
            return True


if __name__ == "__main__":
    w = Gtk.Window()
    w.connect("delete-event", Gtk.main_quit)
    sab = StarArrowButton(
        w, "/home/thomas/Programmering/workspace/pychess/glade/dock_top.svg",
        "/home/thomas/Programmering/workspace/pychess/glade/dock_right.svg",
        "/home/thomas/Programmering/workspace/pychess/glade/dock_bottom.svg",
        "/home/thomas/Programmering/workspace/pychess/glade/dock_left.svg",
        "/home/thomas/Programmering/workspace/pychess/glade/dock_center.svg",
        "/home/thomas/Programmering/workspace/pychess/glade/dock_star.svg")

    def on_expose(widget, event):
        cairo_win = widget.window.cairo_create()
        cx_loc = cy_loc = 100
        radius = 50
        cairo_win.arc(cx_loc, cy_loc, radius - 1, 0, 2 * pi)
        cairo_win.set_source_rgba(1.0, 0.0, 0.0, 1.0)
        cairo_win.set_operator(cairo.OPERATOR_OVER)
        cairo_win.fill()
    # w.connect("e)
    w.show_all()
    sab.show_all()
    Gtk.main()

# if __name__ != "__main__":
#    w = Gtk.Window()
#    w.connect("delete-event", Gtk.main_quit)
#    hbox = Gtk.HBox()
#
#    l = Gtk.Layout()
#    l.set_size_request(200,200)
#    sab = StarArrowButton("/home/thomas/Programmering/workspace/pychess/glade/dock_top.svg",
#                          "/home/thomas/Programmering/workspace/pychess/glade/dock_right.svg",
#                          "/home/thomas/Programmering/workspace/pychess/glade/dock_bottom.svg",
#                          "/home/thomas/Programmering/workspace/pychess/glade/dock_left.svg",
#                          "/home/thomas/Programmering/workspace/pychess/glade/dock_center.svg",
#                          "/home/thomas/Programmering/workspace/pychess/glade/dock_star.svg")
#    sab.set_size_request(200,200)
#    l.put(sab, 0, 0)
#    hbox.add(l)
#    def handle (*args):
#        sab.showAt(l, CENTER)
#    l.connect("button-press-event", handle)
#
#    nb = Gtk.Notebook()
#    label = Gtk.Label(label="hi")
#    nb.append_page(label)
#    nb.set_tab_detachable(label, True)
#    hbox.add(nb)
#    w.add(hbox)
#    w.show_all()
#    Gtk.main()

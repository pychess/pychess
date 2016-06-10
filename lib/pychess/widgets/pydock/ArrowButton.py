from __future__ import absolute_import
from __future__ import print_function

import cairo

from gi.repository import Gtk, GObject, Gdk

from .OverlayWindow import OverlayWindow

from .__init__ import NORTH, EAST, SOUTH, WEST


class ArrowButton(OverlayWindow):
    """ Leafs will connect to the drag-drop signal """

    __gsignals__ = {
        'dropped': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'hovered': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'left': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, parent, svgPath, position):
        OverlayWindow.__init__(self, parent)
        self.myposition = position
        self.svgPath = svgPath

        # targets = [("GTK_NOTEBOOK_TAB", Gtk.TargetFlags.SAME_APP, 0xbadbeef)]
        targets = [Gtk.TargetEntry.new("GTK_NOTEBOOK_TAB",
                                       Gtk.TargetFlags.SAME_APP, 0xbadbeef)]
        self.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                           targets, Gdk.DragAction.MOVE)
        self.drag_dest_set_track_motion(True)
        self.myparent.button_cids[self] += [
            self.connect("drag-motion", self.__onDragMotion),
            self.connect("drag-leave", self.__onDragLeave),
            self.connect("drag-drop", self.__onDragDrop),
            self.connect_after("draw", self.__onExposeEvent),
        ]
        self.hovered = False

        self.myparentAlloc = None
        self.myparentPos = None
        self.hasHole = False

    def _calcSize(self):
        parentAlloc = self.myparent.get_allocation()
        width, height = self.getSizeOfSvg(self.svgPath)

        if self.myparentAlloc is None:
            self.resize(width, height)

        if self.get_window() and not self.hasHole:
            self.hasHole = True
            self.digAHole(self.svgPath, width, height)

        if self.myposition == NORTH:
            x_loc, y_loc = parentAlloc.width / 2. - width / 2., 0
        elif self.myposition == EAST:
            x_loc, y_loc = parentAlloc.width - width, parentAlloc.height / 2. - height / 2.
        elif self.myposition == SOUTH:
            x_loc, y_loc = parentAlloc.width / 2. - width / 2., parentAlloc.height - height
        elif self.myposition == WEST:
            x_loc, y_loc = 0, parentAlloc.height / 2. - height / 2.

        x_loc, y_loc = self.translateCoords(int(x_loc), int(y_loc))
        if (x_loc, y_loc) != self.get_position():
            self.move(x_loc, y_loc)

        self.myparentAlloc = parentAlloc
        self.myparentPos = self.myparent.get_window().get_position()

    def __onExposeEvent(self, self_, ctx):
        self._calcSize()
        context = self.get_window().cairo_create()
        width, height = self.getSizeOfSvg(self.svgPath)
        surface = self.getSurfaceFromSvg(self.svgPath, width, height)

        if self.is_composited():
            context.set_operator(cairo.OPERATOR_CLEAR)
            context.set_source_rgba(0.0, 0.0, 0.0, 0.0)
            context.paint()
            context.set_operator(cairo.OPERATOR_OVER)

        # FIXME
        # mask = Gdk.Pixmap(None, width, height, 1)
        # mcontext = mask.cairo_create()
        # mcontext.set_source_surface(surface, 0, 0)
        # mcontext.paint()
        # self.window.shape_combine_mask(mask, 0, 0)

        context.set_source_surface(surface, 0, 0)
        context.paint()

    def __containsPoint(self, x, y):
        alloc = self.get_allocation()
        return 0 <= x < alloc.width and 0 <= y < alloc.height

    def __onDragMotion(self, arrow, context, x, y, timestamp):
        if not self.hovered and self.__containsPoint(x, y):
            self.hovered = True
            self.emit("hovered", Gtk.drag_get_source_widget(context))
        elif self.hovered and not self.__containsPoint(x, y):
            self.hovered = False
            self.emit("left")

    def __onDragLeave(self, arrow, context, timestamp):
        if self.hovered:
            self.hovered = False
            self.emit("left")

    def __onDragDrop(self, arrow, context, x, y, timestamp):
        if self.__containsPoint(x, y):
            self.emit("dropped", Gtk.drag_get_source_widget(context))
            context.finish(True, True, timestamp)
            return True

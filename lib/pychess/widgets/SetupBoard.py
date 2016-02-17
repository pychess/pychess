from gi.repository import Gtk, Gdk, GObject

from math import floor

from pychess.widgets.BoardView import BoardView
from pychess.Utils.Cord import Cord

ALL = 0


class SetupBoard(Gtk.EventBox):

    __gsignals__ = {
        'cord_clicked': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.view = BoardView()
        self.add(self.view)
        self.view.showEnpassant = True

        self.connect("button_press_event", self.button_press)
        self.connect("button_release_event", self.button_release)
        self.add_events(Gdk.EventMask.LEAVE_NOTIFY_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect("motion_notify_event", self.motion_notify)
        self.connect("leave_notify_event", self.leave_notify)

        self.brush = None

        #          Selection and stuff          #

    def setBrush(self, brush):
        self.brush = brush

    def getBrush(self):
        return self.brush

    def transPoint(self, x_loc, y_loc):
        if not self.view.square:
            return None
        x_coord, y_coord, square, side = self.view.square
        y_loc -= y_coord
        x_loc -= x_coord
        y_loc /= float(side)
        x_loc /= float(side)
        if self.view.fromWhite:
            y_loc = 8 - y_loc
        else:
            x_loc = 8 - x_loc
        return x_loc, y_loc

    def point2Cord(self, x_loc, y_loc):
        if not self.view.square:
            return None
        point = self.transPoint(x_loc, y_loc)
        x_loc = floor(point[0])
        if self.view.fromWhite:
            y_loc = floor(point[1])
        else:
            y_loc = floor(point[1])
        if not (0 <= x_loc <= 7 and 0 <= y_loc <= 7):
            return None
        return Cord(x_loc, y_loc)

    def button_press(self, widget, event):
        self.grab_focus()
        cord = self.point2Cord(event.x, event.y)
        if self.legalCords == ALL or cord in self.legalCords:
            self.view.active = cord
        else:
            self.view.active = None

    def button_release(self, widget, event):
        cord = self.point2Cord(event.x, event.y)
        if cord == self.view.active:
            self.emit('cord_clicked', cord)
        self.view.active = None

    def motion_notify(self, widget, event):
        cord = self.point2Cord(event.x, event.y)
        if cord is None:
            return
        if self.legalCords == ALL or cord in self.legalCords:
            self.view.hover = cord
        else:
            self.view.hover = None

    def leave_notify(self, widget, event):
        a = self.get_allocation()
        if not (0 <= event.x < a.width and 0 <= event.y < a.height):
            self.view.hover = None

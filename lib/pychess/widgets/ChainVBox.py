import cairo

from gi.repository import Gtk, Gdk, GObject

from pychess.System.prefix import addDataPrefix
from pychess.widgets.BoardView import union
from .BorderBox import BorderBox


class ChainVBox(Gtk.VBox):
    """ Inspired by the GIMP chainbutton widget """

    __gsignals__ = {'clicked': (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self):
        GObject.GObject.__init__(self)
        chainline = ChainLine(CHAIN_TOP)
        self.pack_start(chainline, True, True, 0)
        self.button = Gtk.Button()
        self.pack_start(self.button, False, True, 0)
        chainline = ChainLine(CHAIN_BOTTOM)
        self.pack_start(chainline, True, True, 0)

        self.image = Gtk.Image()
        self.image.set_from_file(addDataPrefix("glade/stock-vchain-24.png"))
        self.button.set_image(self.image)
        self.button.set_relief(Gtk.ReliefStyle.NONE)
        self.button.set_property("yalign", 0)
        self._active = True
        self.button.connect("clicked", self.onClicked)

    def getActive(self):
        return self._active

    def setActive(self, active):
        assert isinstance(active, bool)
        self._active = active
        if self._active is True:
            self.image.set_from_file(addDataPrefix(
                "glade/stock-vchain-24.png"))
        else:
            self.image.set_from_file(addDataPrefix(
                "glade/stock-vchain-broken-24.png"))

    active = property(getActive, setActive)

    def onClicked(self, button):
        if self._active is False:
            self.image.set_from_file(addDataPrefix(
                "glade/stock-vchain-24.png"))
            self._active = True
        else:
            self.image.set_from_file(addDataPrefix(
                "glade/stock-vchain-broken-24.png"))
            self._active = False
        self.emit("clicked")


CHAIN_TOP, CHAIN_BOTTOM = range(2)
SHORT_LINE = 2
LONG_LINE = 8


class ChainLine(Gtk.Alignment):
    """ The ChainLine's are the little right-angle lines above and below the chain
        button that visually connect the ChainButton to the widgets who's values
        are "chained" together by the ChainButton being active """

    def __init__(self, position):
        GObject.GObject.__init__(self)
        self.position = position
        self.connect_after("size-allocate", self.on_size_allocate)
        self.connect_after("draw", self.on_draw)
        self.set_size_request(10, 10)
        self.lastRectangle = None

    def on_size_allocate(self, widget, requisition):
        if self.get_window():
            allocation = self.get_allocation()
            rect = Gdk.Rectangle()
            rect.x, rect.y, rect.width, rect.height = (allocation.x, allocation.y,
                                                       allocation.width, allocation.height)
            unionrect = union(self.lastRectangle,
                              rect) if self.lastRectangle is not None else rect
            self.get_window().invalidate_rect(unionrect, True)
            self.get_window().process_updates(True)
            self.lastRectangle = rect

    def on_draw(self, widget, context):
        self.draw(context)
        return False

###
# the original Gtk.Style.paint_polygon() way to draw, like The GIMP does it
###
#    def draw (self, widget, event):
#        a = self.get_allocation()
#        print a.x, a.y, a.width, a.height
#        points = [None, None, None]
#        points[0] = (a.x + a.width/2 - SHORT_LINE, a.y + a.height/2)
#        points[1] = (points[0][0] + SHORT_LINE, points[0][1])
#        points[2] = (points[1][0], self.position == CHAIN_TOP and a.y+a.height-1 or a.y)
#        if self.position == CHAIN_BOTTOM:
#            t = points[0]
#            points[0] = points[2]
#            points[2] = t
#        print points
#        self.points = points
#
#        style = widget.get_style()
#        style.paint_polygon(widget.get_parent_window(),
#                            Gtk.StateType.NORMAL,
#                            Gtk.ShadowType.ETCHED_OUT,
#                            event.area,
#                            widget,
#                            "chainbutton",
#                            points,
#                            False)

    def __toAHalf(self, number):
        """ To draw thin straight lines in cairo that aren't blurry, you have to
            adjust the endpoints by 0.5: http://www.cairographics.org/FAQ/#sharp_lines """
        return int(number) + 0.5

    def draw(self, context):
        allocation = self.get_allocation()
        x_loc = allocation.x
        y_loc = allocation.y
        width = allocation.width - 1
        height = allocation.height

        context.set_source_rgb(.2, .2, .2)
        #        context.rectangle(0, 0, width, height)
        #        context.fill()

        context.move_to(
            self.__toAHalf(x_loc + width / 2.) - LONG_LINE,
            self.__toAHalf(y_loc + height / 2.))
        context.line_to(
            self.__toAHalf(x_loc + width / 2.), self.__toAHalf(y_loc + height / 2.))
        if self.position == CHAIN_TOP:
            context.line_to(
                self.__toAHalf(x_loc + width / 2.),
                self.__toAHalf(float(y_loc + height)))
        else:
            context.line_to(
                self.__toAHalf(x_loc + width / 2.), self.__toAHalf(y_loc + 0.))
        context.set_line_width(1.0)
        context.set_line_cap(cairo.LINE_CAP_ROUND)
        context.set_line_join(cairo.LINE_JOIN_ROUND)
        context.stroke()

    def __str__(self):
        allocation = self.get_allocation()
        chain_str = "ChainLine(%s, %s, %s, %s" % (allocation.x, allocation.y,
                                                  allocation.width, allocation.height)
        chain_str += (self.position == CHAIN_TOP and ", CHAIN_TOP" or ", CHAIN_BOTTOM")
        return chain_str + ")"


if __name__ == "__main__":
    win = Gtk.Window()
    chainvbox = ChainVBox()
    label = Gtk.Label(label="Locked")
    adjustment = Gtk.Adjustment(value=10, upper=100, lower=0, step_increment=1)
    spinbutton1 = Gtk.SpinButton(adjustment=adjustment)
    adjustment = Gtk.Adjustment(value=0, upper=100, lower=0, step_increment=1)
    spinbutton2 = Gtk.SpinButton(adjustment=adjustment)
    table = Gtk.Table(rows=3, columns=2)
    #    table.attach(label,0,2,0,1)
    #    table.attach(chainvbox,1,2,1,3)
    #    table.attach(spinbutton1,0,1,1,2)
    #    table.attach(spinbutton2,0,1,2,3)
    table.attach(label, 0, 2, 0, 1, xoptions=Gtk.AttachOptions.SHRINK)
    table.attach(chainvbox, 1, 2, 1, 3, xoptions=Gtk.AttachOptions.SHRINK)
    table.attach(spinbutton1, 0, 1, 1, 2, xoptions=Gtk.AttachOptions.SHRINK)
    table.attach(spinbutton2, 0, 1, 2, 3, xoptions=Gtk.AttachOptions.SHRINK)
    table.set_row_spacings(2)

    def onChainBoxClicked(*whatever):
        if chainvbox.active is False:
            label.set_label("Unlocked")
        else:
            label.set_label("Locked")

    chainvbox.connect("clicked", onChainBoxClicked)
    border_box = BorderBox(widget=table)
    win.add(border_box)
    #    win.resize(150,100)
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()

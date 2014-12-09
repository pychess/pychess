import cairo
import gtk
from gtk import gdk
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE
from pychess.System.prefix import addDataPrefix
from pychess.System.idle_add import idle_add
from BorderBox import BorderBox

class ChainVBox (gtk.VBox):
    """ Inspired by the GIMP chainbutton widget """

    __gsignals__ = {
        'clicked' : (SIGNAL_RUN_FIRST, TYPE_NONE, ())
    }

    def __init__ (self):
        gtk.VBox.__init__(self)
        chainline = ChainLine(CHAIN_TOP)
        self.pack_start(chainline)
        self.button = gtk.Button()
        self.pack_start(self.button, expand=False)
        chainline = ChainLine(CHAIN_BOTTOM)
        self.pack_start(chainline)
        
        self.image = gtk.Image()
        self.image.set_from_file(addDataPrefix("glade/stock-vchain-24.png"))
        self.button.set_image(self.image)
        self.button.set_relief(gtk.RELIEF_NONE)
        self.button.set_property("yalign", 0)
        self._active = True
        self.button.connect("clicked", self.onClicked)
    
    def getActive (self):
        return self._active
    def setActive (self, active):
        assert type(active) is bool
        self._active = active
        if self._active is True:
            self.image.set_from_file(addDataPrefix("glade/stock-vchain-24.png"))
        else:
            self.image.set_from_file(addDataPrefix("glade/stock-vchain-broken-24.png"))
    active = property(getActive, setActive)
    
    def onClicked (self, button):
        if self._active is False:
            self.image.set_from_file(addDataPrefix("glade/stock-vchain-24.png"))
            self._active = True
        else:
            self.image.set_from_file(addDataPrefix("glade/stock-vchain-broken-24.png"))
            self._active = False
        self.emit("clicked")

CHAIN_TOP, CHAIN_BOTTOM = range(2)
SHORT_LINE = 2
LONG_LINE = 8
class ChainLine (gtk.Alignment):
    """ The ChainLine's are the little right-angle lines above and below the chain
        button that visually connect the ChainButton to the widgets who's values
        are "chained" together by the ChainButton being active """
        
    def __init__ (self, position):
        gtk.Alignment.__init__(self)
        self.position = position
        self.connect_after("size-allocate", self.onSizeAllocate)
        self.connect_after("expose-event", self.onExpose)
        self.set_flags(gtk.NO_WINDOW)
        self.set_size_request(10,10)
        self.lastRectangle = None

    @idle_add
    def onSizeAllocate(self, widget, requisition):
        if self.window:
            a = self.get_allocation()
            rect = gdk.Rectangle(a.x, a.y, a.width, a.height)
            unionrect = self.lastRectangle.union(rect) if self.lastRectangle != None else rect
            self.window.invalidate_rect(unionrect, True)
            self.window.process_updates(True)
            self.lastRectangle = rect
        
    def onExpose (self, widget, event):
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
        context.clip()
        self.draw(context)
        return False

###
### the original gtk.Style.paint_polygon() way to draw, like The GIMP does it
###
#    def draw (self, widget, event):
#        a = self.get_allocation()
##        print a.x, a.y, a.width, a.height
#        points = [None, None, None]
#        points[0] = (a.x + a.width/2 - SHORT_LINE, a.y + a.height/2)
#        points[1] = (points[0][0] + SHORT_LINE, points[0][1])
#        points[2] = (points[1][0], self.position == CHAIN_TOP and a.y+a.height-1 or a.y)
#        if self.position == CHAIN_BOTTOM:
#            t = points[0]
#            points[0] = points[2]
#            points[2] = t
##        print points
#        self.points = points
#        
#        style = widget.get_style()
#        style.paint_polygon(widget.get_parent_window(),
#                            gtk.STATE_NORMAL,
#                            gtk.SHADOW_ETCHED_OUT,
#                            event.area,
#                            widget,
#                            "chainbutton",
#                            points,
#                            False)

    def __toAHalf (self, number):
        """ To draw thin straight lines in cairo that aren't blurry, you have to
            adjust the endpoints by 0.5: http://www.cairographics.org/FAQ/#sharp_lines """
        return int(number) + 0.5
    
    def draw (self, context):
        r = self.get_allocation()
        x = r.x
        y = r.y
        width = r.width - 1
        height = r.height
        
        context.set_source_rgb(.2, .2, .2)
#        context.rectangle(0, 0, width, height)
#        context.fill()
        
        context.move_to(self.__toAHalf(x+width/2.)-LONG_LINE, self.__toAHalf(y+height/2.))
        context.line_to(self.__toAHalf(x+width/2.), self.__toAHalf(y+height/2.))
        if self.position == CHAIN_TOP:
            context.line_to(self.__toAHalf(x+width/2.), self.__toAHalf(float(y+height)))
        else:
            context.line_to(self.__toAHalf(x+width/2.), self.__toAHalf(y+0.))
        context.set_line_width(1.0)
        context.set_line_cap(cairo.LINE_CAP_ROUND)
        context.set_line_join(cairo.LINE_JOIN_ROUND)
        context.stroke()

    def __str__ (self):
        a = self.get_allocation()
        s = "ChainLine(%s, %s, %s, %s" % (a.x, a.y, a.width, a.height)
#        if self.points != None:
#            points = []
#            for a in self.points:
#                points.append("(%s, %s)" % (a[0], a[1]))
#            s += ", (" + ", ".join(points) + ")"
        s += (self.position == CHAIN_TOP and ", CHAIN_TOP" or ", CHAIN_BOTTOM")
        return s + ")"
    
if __name__ == "__main__":
    win = gtk.Window()
    chainvbox = ChainVBox()
    label = gtk.Label("Locked")
    adjustment = gtk.Adjustment(value=10, upper=100, lower=0, step_incr=1)
    spinbutton1 = gtk.SpinButton(adjustment=adjustment)
    adjustment = gtk.Adjustment(value=0, upper=100, lower=0, step_incr=1)
    spinbutton2 = gtk.SpinButton(adjustment=adjustment)
    table = gtk.Table(rows=3,columns=2)
#    table.attach(label,0,2,0,1)
#    table.attach(chainvbox,1,2,1,3)
#    table.attach(spinbutton1,0,1,1,2)
#    table.attach(spinbutton2,0,1,2,3)
    table.attach(label,0,2,0,1,xoptions=gtk.SHRINK)
    table.attach(chainvbox,1,2,1,3,xoptions=gtk.SHRINK)
    table.attach(spinbutton1,0,1,1,2,xoptions=gtk.SHRINK)
    table.attach(spinbutton2,0,1,2,3,xoptions=gtk.SHRINK)
    table.set_row_spacings(2)
    def onChainBoxClicked (*whatever):
        if chainvbox.active == False:
            label.set_label("Unlocked")
        else:
            label.set_label("Locked")
    chainvbox.connect("clicked", onChainBoxClicked)
    bb = BorderBox(widget=table)
    win.add(bb)
#    win.resize(150,100)
    win.connect("delete-event", gtk.main_quit)
    win.show_all()
    gtk.main()

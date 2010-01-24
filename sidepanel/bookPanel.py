import gtk, gobject, cairo

from pychess.System import conf
from pychess.Utils.book import getOpenings
from pychess.Utils.Move import parseSAN, toSAN, toFAN
from pychess.System.prefix import addDataPrefix

__title__ = _("Opening Book")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _("The opening book will try to inspire you during the opening phase of the game by showing you common moves made by chess masters")

__about__ = _("Official PyChess panel.")

class Sidepanel:
    
    def load (self, gmwidg):
        widgets = gtk.glade.XML(addDataPrefix("sidepanel/book.glade"))
        self.tv = widgets.get_widget("treeview")
        self.sw = widgets.get_widget("scrolledwindow")
        self.sw.unparent()
        
        self.store = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
        self.tv.set_model(self.store)
        
        self.tv.append_column(gtk.TreeViewColumn(
                "Move", gtk.CellRendererText(), text=0))
        r = gtk.CellRendererText()
        r.set_property("xalign", 1)
        self.tv.append_column(gtk.TreeViewColumn("Games", r, text=1))
        self.tv.append_column(gtk.TreeViewColumn(
                "Win/Draw/Loss", BookCellRenderer(), data=2))
        
        self.boardcontrol = gmwidg.board
        self.board = self.boardcontrol.view
        self.board.connect("shown_changed", self.shown_changed)
        self.tv.connect("cursor_changed", self.selection_changed)
        self.tv.connect("select_cursor_row", self.selection_changed)
        self.tv.connect("row-activated", self.row_activated)
        self.tv.connect("query-tooltip", self.query_tooltip)
        
        self.tv.props.has_tooltip = True
        
        self.shown_changed(self.board, 0)
        
        return self.sw
    
    def shown_changed (self, board, shown):
        self.openings = getOpenings(self.board.model.getBoardAtPly(shown))
        self.openings.sort(lambda a, b: sum(b[1:])-sum(a[1:]))
        
        self.board.bluearrow = None
        self.store.clear()
        
        if not self.openings and self.sw.get_child() == self.tv:
            self.sw.remove(self.tv)
            label = gtk.Label(_("In this position,\nthere is no book move."))
            label.set_property("yalign",0.1)
            self.sw.add_with_viewport(label)
            self.sw.get_child().set_shadow_type(gtk.SHADOW_NONE)
            self.sw.show_all()
            return
        
        if self.openings and self.sw.get_child() != self.tv:
            self.sw.remove(self.sw.get_child())
            self.sw.add(self.tv)
        
        i = 0
        for move, wins, draws, loses in self.openings:
            games = wins+draws+loses
            if not games: continue
            wins, draws, loses = \
                    map(lambda x: x/float(games), (wins, draws, loses))
            b = self.board.model.getBoardAtPly(shown)
            if conf.get("figuresInNotation", False):
                move = toFAN(b, parseSAN(b, move))
            else:
                move = toSAN(b, parseSAN(b, move), True)
            self.store.append ([move, str(games), (wins,draws,loses)])
    
    def selection_changed (self, widget, *args):
        
        iter = self.tv.get_selection().get_selected()[1]
        if iter == None:
            self.board.bluearrow = None
            return
        else: sel = self.tv.get_model().get_path(iter)[0]
        
        move = parseSAN (
            self.board.model.boards[self.board.shown], self.openings[sel][0] )
        self.board.bluearrow = move.cords
    
    def row_activated (self, widget, *args):
        if len(self.board.model.boards) < self.board.shown+1:
            return
        arrow = self.board.bluearrow
        if arrow and self.board.model.ply == self.board.shown:
            self.board.bluearrow = None
            self.boardcontrol.emit_move_signal(*arrow)
    
    def query_tooltip(self, treeview, x, y, keyboard_mode, tooltip):
        # First, find out where the pointer is:
        path_col_x_y = treeview.get_path_at_pos (x, y);

        # If we're not pointed at a row, then return FALSE to say
        # "don't show a tip".
        if not path_col_x_y:
            return False
        
        # Otherwise, ask the TreeView to set up the tip's area according
        # to the row's rectangle.
        path, col, x, y = path_col_x_y
        treeview.set_tooltip_row(tooltip, path);

        # And then load it up with some meaningful text.
        iter = self.store.get_iter(path)
        w, d, l = self.store.get(iter, 2)[0]
        tooltip.set_markup('Wins: <b>%0.1f%%</b>\nDraws: <b>%0.1f%%</b>\nLoses: <b>%0.1f%%</b>' %
                           (w*100, d*100, l*100))
        
        # Return true to say "show the tip".
        return True;

################################################################################
# BookCellRenderer                                                             #
################################################################################

width, height = 80, 23
class BookCellRenderer (gtk.GenericCellRenderer):
    __gproperties__ = {
        "data": (gobject.TYPE_PYOBJECT, "Data", "Data", gobject.PARAM_READWRITE),
    }
    
    def __init__(self):
        self.__gobject_init__()
        self.data = None
        
    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)
        
    def do_get_property(self, pspec):
        return getattr(self, pspec.name)
        
    def on_render(self, window, widget, background_area, cell_area, expose_area, flags):
        if not self.data: return
        cairo = window.cairo_create()
        w,d,l = self.data
        paintGraph(cairo, w, d, l, cell_area)
       
    def on_get_size(self, widget, cell_area=None):
        return (0, 0, width, height)
            
gobject.type_register(BookCellRenderer)

################################################################################
# BookCellRenderer functions                                                   #
################################################################################

from math import ceil

def paintGraph (cairo,win,draw,loss,rect):
    x,y,w,h = rect.x, rect.y, rect.width, rect.height

    cairo.save()
    cairo.rectangle(x,y,ceil(win*w),h)
    cairo.clip()
    pathBlock(cairo, x,y,w,h)
    cairo.set_source_rgb(0.9,0.9,0.9)
    cairo.fill()
    cairo.restore()
    
    cairo.save()
    cairo.rectangle(x+win*w,y,ceil(draw*w),h)
    cairo.clip()
    pathBlock(cairo, x,y,w,h)
    cairo.set_source_rgb(0.45,0.45,0.45)
    cairo.fill()
    cairo.restore()
    
    cairo.save()
    cairo.rectangle(x+win*w+draw*w,y,loss*w,h)
    cairo.clip()
    pathBlock(cairo, x,y,w,h)
    cairo.set_source_rgb(0,0,0)
    cairo.fill()
    cairo.restore()
    
    cairo.save()
    cairo.rectangle(x,y,w,h)
    cairo.clip()
    pathBlock(cairo, x,y,w,h)
    cairo.set_source_rgb(1,1,1)
    cairo.stroke()
    cairo.restore()

def pathBlock (cairo, x,y,w,h):
    cairo.move_to(x+10, y)
    cairo.rel_line_to(w-20, 0)
    cairo.rel_curve_to(10, 0, 10, 0, 10, 10)
    cairo.rel_line_to(0, 3)
    cairo.rel_curve_to(0, 10, 0, 10, -10, 10)
    cairo.rel_line_to(-w+20, 0)
    cairo.rel_curve_to(-10, 0, -10, 0, -10, -10)
    cairo.rel_line_to(0, -3)
    cairo.rel_curve_to(0, -10, 0, -10, 10, -10)

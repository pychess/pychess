import gtk, gobject, cairo

from pychess.System import conf
from pychess.Utils.const import WHITE
from pychess.Utils.book import getOpenings
from pychess.Utils.Move import Move, toSAN, toFAN
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
        self.tv.append_column(gtk.TreeViewColumn("Popularity", r, text=1))
        self.tv.append_column(gtk.TreeViewColumn(
                "Success", BookCellRenderer(), data=2))
        
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
        self.openings = getOpenings(self.board.model.getBoardAtPly(shown).board)
        self.openings.sort(key=lambda t: t[1], reverse=True)
        
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
        
        totalWeight = 0
        # Polyglot-formatted books have space for learning data.
        # Polyglot stores performance history, but this convention is not
        # required. We will display this info if it passes a sanity-check.
        # TODO: Maybe this should be smarter. One idea is to switch off the
        # display for later moves once we see learning data that don't fit
        # the formula we're looking for.
        historyExists = False
        historyIsPlausible = True
        maxGames = 1
        for move, weight, games, score in self.openings:
            totalWeight += weight
            maxGames = max(games, maxGames)
            historyExists = historyExists or games > 0
            historyIsPlausible = historyIsPlausible and score < 2*games < 65536

        for move, weight, games, score in self.openings:
            b = self.board.model.getBoardAtPly(shown)
            if conf.get("figuresInNotation", False):
                move = toFAN(b, Move(move))
            else:
                move = toSAN(b, Move(move), True)
            if weight <= totalWeight / 100:
                popularity = "?"
            else:
                popularity = "%0.1f%%" % (weight*100.0/totalWeight)
            if not (historyExists and historyIsPlausible):
                games = 0
            w =        score*0.5  / maxGames
            l = (games-score*0.5) / maxGames
            history = b.color == WHITE and (w, l, games) or (l, w, games)
            self.store.append ([move, popularity, history])
    
    def selection_changed (self, widget, *args):
        
        iter = self.tv.get_selection().get_selected()[1]
        if iter == None:
            self.board.bluearrow = None
            return
        else: sel = self.tv.get_model().get_path(iter)[0]
        
        move = Move(self.openings[sel][0])
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
        path_col_x_y = treeview.get_path_at_pos (x, y)

        # If we're not pointed at a row, then return FALSE to say
        # "don't show a tip".
        if not path_col_x_y:
            return False
        
        # Otherwise, ask the TreeView to set up the tip's area according
        # to the row's rectangle.
        path, col, x, y = path_col_x_y
        treeview.set_tooltip_row(tooltip, path)

        # And then load it up with some meaningful text.
        iter = self.store.get_iter(path)
        w_win, b_win, games = self.store.get(iter, 2)[0]
        if games:
            history = _("White scores <b>%0.1f</b>%% - <b>%0.1f</b>%%\n") % \
                      (100*w_win / (w_win + b_win), 100*b_win / (w_win + b_win))
            if games > 1:
                confidence = _("Based on %d games") % games
            else:
                confidence = _("Based on 1 game")
            tooltip.set_markup(history + confidence)
            return True # Show the tip.
        
        return False

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
        w_win, b_win, games = self.data
        if games:
            paintGraph(cairo, w_win, b_win, cell_area)
       
    def on_get_size(self, widget, cell_area=None):
        return (0, 0, width, height)
            
gobject.type_register(BookCellRenderer)

################################################################################
# BookCellRenderer functions                                                   #
################################################################################

from math import ceil

def paintGraph (cairo, w_win, b_win, rect):
    x,y,w0,h = rect.x, rect.y, rect.width, rect.height
    w = ceil((w_win + b_win) * w0)

    if w_win > 0:
        cairo.save()
        cairo.rectangle(x,y,w_win*w0,h)
        cairo.clip()
        pathBlock(cairo, x,y,w,h)
        cairo.set_source_rgb(0.9,0.9,0.9)
        cairo.fill()
        cairo.restore()
    
    if b_win > 0:
        cairo.save()
        cairo.rectangle(x+w_win*w0,y,b_win*w0,h)
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

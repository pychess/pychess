import gtk, gobject, cairo, pango

from pychess.System import conf
from pychess.Utils.const import *
from pychess.Utils.book import getOpenings
from pychess.Utils.logic import legalMoveCount
from pychess.Utils.EndgameTable import EndgameTable
from pychess.Utils.Move import Move, toSAN, toFAN, parseAny
from pychess.System.prefix import addDataPrefix

__title__ = _("Hints")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _("The hint panel will provide computer advice during each stage of the game")

__about__ = _("Official PyChess panel.")

class Advisor:
    def __init__ (self, store, name):
        self.store = store
        iter = store.append(None, ["", ("", 0, None), name])
        self.path = store.get_path(iter)
    
    def shown_changed (self, board, shown):
        raise NotImplementedError
    
    def child_tooltip (self, i):
        return ""
    
    def query_tooltip (self, subpath):
        if not subpath:
            return self.tooltip
        return self.child_tooltip(subpath[0])
    
    def empty_parent (self):
        while True:
            parent = self.store.get_iter(self.path)
            child = self.store.iter_children(parent)
            if not child:
                return parent
            self.store.remove(child)
    
    def pause (self):
        pass

class OpeningAdvisor(Advisor):
    def __init__ (self, store):
        Advisor.__init__(self, store, _("Opening Book"))
        self.tooltip = _("The opening book will try to inspire you during the opening phase of the game by showing you common moves made by chess masters")
    
    def shown_changed (self, board, shown):
        m = board.model
        b = m.getBoardAtPly(shown)
        parent = self.empty_parent()
        
        openings = getOpenings(b.board)
        openings.sort(key=lambda t: t[1], reverse=True)
        if not openings: return
        
        totalWeight = 0.0
        # Polyglot-formatted books have space for learning data.
        # See version ac31dc37ec89 for an attempt to parse it.
        # In this version, we simply ignore it. (Most books don't have it.)
        for move, weight, games, score in openings:
            totalWeight += weight

        for move, weight, games, score in openings:
            if conf.get("figuresInNotation", False):
                move = toFAN(b, Move(move))
            else:
                move = toSAN(b, Move(move), True)
            weight /= totalWeight
            weightText = "%0.1f%%" % (100 * weight)
            goodness = min(weight * len(openings), 1.0)
            
            variationName = "" # TODO
            self.store.append (parent, [move, (weightText, 1, goodness), variationName])
    
    def child_tooltip (self, i):
        # TODO: try to find a name for the opening
        return ""

class EndgameAdvisor(Advisor):
    def __init__ (self, store):
        Advisor.__init__(self, store, _("Endgame Table"))
        self.egtb = EndgameTable()
        self.tooltip = _("The endgame table will show exact analysis when there are few pieces on the board.")
        # TODO: Show a message if tablebases for the position exist but are neither installed nor allowed.
    
    def shown_changed (self, board, shown):
        m = board.model
        b = m.getBoardAtPly(shown)
        parent = self.empty_parent()
        
        endings = self.egtb.scoreAllMoves(b.board)
        for move, result, depth in endings:
            if conf.get("figuresInNotation", False):
                move = toFAN(b, move)
            else:
                move = toSAN(b, move, True)
            
            if result == DRAW:
                result = (_("Draw"), 1, 0.5)
                details = ""
            elif (result == WHITEWON) ^ (b.color == WHITE):
                result = (_("Loss"), 1, 0.0)
                details = _("Mate in %d") % depth
            else:
                result = (_("Win"), 1, 1.0)
                details = _("Mate in %d") % depth
            self.store.append(parent, [move, result, details])

class Sidepanel:
    
    def load (self, gmwidg):
        widgets = gtk.glade.XML(addDataPrefix("sidepanel/book.glade"))
        self.tv = widgets.get_widget("treeview")
        self.sw = widgets.get_widget("scrolledwindow")
        self.sw.unparent()
        
        self.store = gtk.TreeStore(str, gobject.TYPE_PYOBJECT, str)
        self.tv.set_model(self.store)
        
        self.tv.append_column(gtk.TreeViewColumn(
                "Move", gtk.CellRendererText(), text=0))
        self.tv.append_column(gtk.TreeViewColumn(
                "Strength", StrengthCellRenderer(), data=1))
        self.tv.append_column(gtk.TreeViewColumn(
                "Details", gtk.CellRendererText(), text=2))
        
        self.boardcontrol = gmwidg.board
        self.board = self.boardcontrol.view
        self.board.connect("shown_changed", self.shown_changed)
        self.tv.connect("cursor_changed", self.selection_changed)
        self.tv.connect("select_cursor_row", self.selection_changed)
        self.tv.connect("row-activated", self.row_activated)
        self.tv.connect("query-tooltip", self.query_tooltip)
        
        self.tv.props.has_tooltip = True
        
        self.advisors = [ OpeningAdvisor(self.store) ]
        #if HINT in gmwidg.gamemodel.spectactors:
            #self.advisors.append(EngineAdvisor(self.store, gmwidg.gamemodel.spectactors[HINT], ANALYZING))
        self.advisors.append(EndgameAdvisor(self.store))
        #if SPY in gmwidg.gamemodel.spectactors:
            #self.advisors.append(EngineAdvisor(self.store, gmwidg.gamemodel.spectactors[SPY], INVERSE_ANALYZING))
        
        self.shown_changed(self.board, 0)
        
        return self.sw
    
    def shown_changed (self, board, shown):
        board.bluearrow = None
        
        if legalMoveCount(board.model.getBoardAtPly(shown)) == 0:
            if self.sw.get_child() == self.tv:
                self.sw.remove(self.tv)
                label = gtk.Label(_("In this position,\nthere is no legal move."))
                label.set_property("yalign",0.1)
                self.sw.add_with_viewport(label)
                self.sw.get_child().set_shadow_type(gtk.SHADOW_NONE)
                self.sw.show_all()
                for advisor in self.advisors:
                    advisor.pause()
            return
        
        for advisor in self.advisors:
            advisor.shown_changed(board, shown)
        self.tv.expand_all()
        
        if self.sw.get_child() != self.tv:
            self.sw.remove(self.sw.get_child())
            self.sw.add(self.tv)

    def selection_changed (self, widget, *args):
        # TODO: replace this hack with a call to an advisor method.
        iter = self.tv.get_selection().get_selected()[1]
        if iter == None:
            self.board.bluearrow = None
            return
        else: sel = self.tv.get_model().get_path(iter)[0]
        
        b = self.board.model.getBoardAtPly(self.board.shown)
        movetext = self.store.get(iter, 0)[0]
        if not movetext or movetext == "...":
            return
        move = parseAny(b, movetext)
        self.board.bluearrow = move.cords
    
    def row_activated (self, widget, *args):
        # TODO: replace this hack with a call to an advisor method.
        iter = self.tv.get_selection().get_selected()[1]
        if self.board.model.ply != self.board.shown or iter is None:
            return
        movetext = self.store.get(iter, 0)[0]
        if not movetext or movetext == "...":
            return
        self.board.bluearrow = None
        b = self.board.model.boards[-1]
        move = parseAny(b, movetext)
        self.boardcontrol.emit("piece_moved", move, b.color)
    
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
        
        # And ask the advisor for some text
        iter = self.store.get_iter(path)
        text = self.advisors[path[0]].query_tooltip(path[1:])
        if text:
            tooltip.set_markup(text)
            return True # Show the tip.
            
        return False

################################################################################
# StrengthCellRenderer                                                         #
################################################################################

width, height = 80, 23
class StrengthCellRenderer (gtk.GenericCellRenderer):
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
        text, widthfrac, goodness = self.data
        if widthfrac:
            paintGraph(cairo, widthfrac, stoplightColor(goodness), cell_area)
        if text:
            layout = widget.create_pango_layout(text)
            w, h = layout.get_pixel_size()
            context = widget.create_pango_context()
            cairo.move_to(cell_area.x, cell_area.y)
            cairo.rel_move_to( 50 - w, (height - h) / 2)
            cairo.show_layout(layout)
       
    def on_get_size(self, widget, cell_area=None):
        return (0, 0, width, height)
            
gobject.type_register(StrengthCellRenderer)

################################################################################
# StrengthCellRenderer functions                                               #
################################################################################

from math import ceil

def stoplightColor (x):
    interp = lambda y0, yh, y1 : y0 + (y1+4*yh-3*y0) * x  + (-4*yh+2*y0) * x*x
    r = interp(239, 252, 138) / 255
    g = interp( 41, 233, 226) / 255 
    b = interp( 41,  79,  52) / 255
    return r, g, b

def paintGraph (cairo, widthfrac, rgb, rect):
    x,y,w0,h = rect.x, rect.y, rect.width, rect.height
    w = ceil(widthfrac * w0)
    
    cairo.save()
    cairo.rectangle(x,y,w,h)
    cairo.clip()
    cairo.move_to(x+10, y)
    cairo.rel_line_to(w-20, 0)
    cairo.rel_curve_to(10, 0, 10, 0, 10, 10)
    cairo.rel_line_to(0, 3)
    cairo.rel_curve_to(0, 10, 0, 10, -10, 10)
    cairo.rel_line_to(-w+20, 0)
    cairo.rel_curve_to(-10, 0, -10, 0, -10, -10)
    cairo.rel_line_to(0, -3)
    cairo.rel_curve_to(0, -10, 0, -10, 10, -10)
    cairo.set_source_rgb(*rgb)
    cairo.fill()
    cairo.restore()

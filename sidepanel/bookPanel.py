import gtk, gobject, cairo, pango

from pychess.System import conf
from pychess.Utils.const import *
from pychess.Utils.book import getOpenings
from pychess.Utils.logic import legalMoveCount
from pychess.Utils.EndgameTable import EndgameTable
from pychess.Utils.Move import Move, toSAN, toFAN, parseAny, listToSan
from pychess.System.prefix import addDataPrefix

# TODO: move this functionality elsewhere
from pychess.Utils.lutils.ldata import MATE_VALUE

def prettyPrintScore (s):
    if s is None: return "?"
    if s == 0: return "0.00"
    if s > 0:
       pp = "+"
    else:
        pp = "-"
        s = -s
    
    if s >= MATE_VALUE - 1000:
        return pp + "#" + str(MATE_VALUE - s)
    else:
        return pp + "%0.2f" % (s / 100.0)

__title__ = _("Hints")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _("The hint panel will provide computer advice during each stage of the game")

__about__ = _("Official PyChess panel.")

class Advisor:
    def __init__ (self, store, name):
        self.store = store
        iter = store.append(None, [None, ("", 0, None), name])
        self.path = store.get_path(iter)
    
    def shown_changed (self, board, shown):
        """ Update the suggestions to match a changed position. """
        pass
    
    def game_changed (self, board, model):
        """ Update the suggestions after a player move / undo. """
        pass
    
    def child_tooltip (self, i):
        """ Return a tooltip (or empty) string for the given child row. """
        return ""
    
    def row_activated (self, path):
        """ Act on a double-clicked child row other than a move suggestion. """
        pass
    
    def query_tooltip (self, path):
        if not path[1:]:
            return self.tooltip
        return self.child_tooltip(path[1])
    
    def empty_parent (self):
        while True:
            parent = self.store.get_iter(self.path)
            child = self.store.iter_children(parent)
            if not child:
                return parent
            del self.store[child]

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
            weight /= totalWeight
            goodness = min(weight * len(openings), 1.0)
            weight = "%0.1f%%" % (100 * weight)
            
            eco = "" # TODO
            self.store.append(parent, [Move(move), (weight, 1, goodness), eco])
    
    def child_tooltip (self, i):
        # TODO: try to find a name for the opening
        return ""

class EngineAdvisor(Advisor):
    # An EngineAdvisor always has self.linesExpected rows reserved for analysis.
    def __init__ (self, store, engine, mode):
        if mode == ANALYZING:
            Advisor.__init__(self, store, _("Analysis by %s") % engine)
            self.tooltip = _("%s will try to predict which move is best and which side has the advantage" % engine)
        else:
            Advisor.__init__(self, store, _("Threat analysis by %s") % engine)
            self.tooltip = _("%s will identify what threats would exist if it were your opponent's turn to move" % engine)
        self.engine = engine
        self.mode = mode
        self.active = False
        self.analysisIsFresh = True
        self.linesExpected   = 1
        self.linesMax        = 1
        self.offeringExtraPV = False
        self.store.append(self.empty_parent(), [None, ("", 0, None), _("Calculating...")])
        self.connection = engine.connect("analyze", self.on_analyze)
    
    def __del__ (self):
        self.engine.disconnect(self.connection)
    
    def only_child (self):
        if self.offeringExtraPV:
            parent = self.store.get_iter(self.path)
            child = self.store.iter_children(parent)
            del self.store[child]
            self.offeringExtraPV = False
        for line in xrange(self.linesExpected):
            parent = self.store.get_iter(self.path)
            child = self.store.iter_children(parent)
            if line == self.linesExpected - 1:
                return child
            del self.store[child]
    
    def game_changed (self, board, model):
        self.analysisIsFresh = False
        if (model.ply == board.shown):
            self.shown_changed(board, board.shown) # Undo doesn't emit shown_changed
    
    def shown_changed (self, board, shown):
        m = board.model
        b = m.getBoardAtPly(shown)
        
        if board.model.ply != shown:
            if not self.active: return
            self.active = False
            child = self.only_child()
            # TODO: allow user to switch to visible position.
            self.store[child] = [None, ("", 0, None), _("The engine is considering another position.")]
            return
        
        self.board = b if self.mode != INVERSE_ANALYZING else b.switchColor()
        self.active = True
        if self.analysisIsFresh and self.engine.getAnalysis():
            # Allocate rows for the analysis lines
            for line in xrange(self.linesExpected-1):
                parent = self.store.get_iter(self.path)
                self.store.append(parent, [None, ("", 0, None), _("Calculating...")])
            self.on_analyze(self.engine, self.engine.getAnalysis())
        else:
            child = self.only_child()
            self.store[child] = [None, ("", 0, None), _("Calculating...")]
            self.engine.requestMultiPV(1)
            self.linesExpected   = 1
            self.offeringExtraPV = False
            self.linesMax = min(self.engine.maxAnalysisLines(), legalMoveCount(self.board))
    
    def on_analyze (self, engine, analysis):
        self.analysisIsFresh = True
        if not self.active: return
        for i, line in enumerate(analysis):
            pv, score = line
            move = None
            if pv:
                move = pv[0]
            pv = " ".join(listToSan(self.board, pv))
            if self.board.color == BLACK: score = -score
            # TODO make a move's "goodness" relative to other moves or past scores
            goodness = (min(max(score, -250), 250) + 250) / 500.0
            self.store[self.path + (i,)] = [move, (prettyPrintScore(score), 1, goodness), pv]
        
        if not self.offeringExtraPV and self.linesExpected <= len(analysis) < self.linesMax:
            parent = self.store.get_iter(self.path)
            self.store.append(parent, [None, ("", 0, None), _("Double-click for another suggestion.")])
            self.offeringExtraPV = True
    
    def row_activated (self, path):
        if self.active and path[1:] and path[1] == self.linesExpected:
            self.linesExpected += 1
            self.offeringExtraPV = False
            self.engine.requestMultiPV(self.linesExpected)
            self.store[path] = [None, ("", 0, None), _("Calculating...")]
    
    def child_tooltip (self, i):
        if self.active:
            if i < self.linesExpected:
                return _("Engine scores are in units of pawns, from White's point of view.")
            else:
                return _("Adding suggestions can help you find ideas, but slows down the computer's analysis.")
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
        self.boardcontrol = gmwidg.board
        self.board = self.boardcontrol.view
        
        widgets = gtk.glade.XML(addDataPrefix("sidepanel/book.glade"))
        self.tv = widgets.get_widget("treeview")
        self.sw = widgets.get_widget("scrolledwindow")
        self.sw.unparent()
        self.store = gtk.TreeStore(gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, str)
        self.tv.set_model(self.store)
        
        moveRenderer = gtk.CellRendererText()
        c0 = gtk.TreeViewColumn("Move", moveRenderer)
        c1 = gtk.TreeViewColumn("Strength", StrengthCellRenderer(), data=1)
        c2 = gtk.TreeViewColumn("Details", gtk.CellRendererText(), text=2)
        
        def getMoveText(column, cell, store, iter, board):
            move = store[iter][0]
            b = board.model.getBoardAtPly(board.shown)
            # Make sure the board's side to move matches the move.
            piece = move and b[move.cords[0]]
            if not piece:
                cell.set_property("text", "")
            else:
                if b.color != b[move.cords[0]].color:
                    b = b.switchColor()
                if conf.get("figuresInNotation", False):
                    cell.set_property("text", toFAN(b, move))
                else:
                    cell.set_property("text", toSAN(b, move, True))
        
        c0.set_cell_data_func(moveRenderer, getMoveText, self.board)
        
        self.tv.append_column(c0)
        self.tv.append_column(c1)
        self.tv.append_column(c2)
        
        self.board.connect("shown_changed", self.shown_changed)
        self.board.model.connect("game_changed", self.game_changed)
        self.board.model.connect("moves_undone", lambda model, moves: self.game_changed(model))
        self.tv.connect("cursor_changed", self.selection_changed)
        self.tv.connect("select_cursor_row", self.selection_changed)
        self.tv.connect("row-activated", self.row_activated)
        self.tv.connect("query-tooltip", self.query_tooltip)
        
        self.tv.props.has_tooltip = True
        
        self.advisors = [ OpeningAdvisor(self.store) ]
        if HINT in gmwidg.gamemodel.spectators:
            self.advisors.append(EngineAdvisor(self.store, gmwidg.gamemodel.spectators[HINT], ANALYZING))
        self.advisors.append(EndgameAdvisor(self.store))
        if SPY in gmwidg.gamemodel.spectators:
            self.advisors.append(EngineAdvisor(self.store, gmwidg.gamemodel.spectators[SPY], INVERSE_ANALYZING))
        
        self.gmwidg = None # HACK
        self.shown_changed(self.board, 0)
        self.gmwidg = gmwidg # HACK
        
        return self.sw
    
    def game_changed (self, model):
        for advisor in self.advisors:
            advisor.game_changed(self.board, model)
    
    def shown_changed (self, board, shown):
# HACK
        if self.gmwidg:
            if HINT in self.gmwidg.gamemodel.spectators:
                self.advisors.append(EngineAdvisor(self.store, self.gmwidg.gamemodel.spectators[HINT], ANALYZING))
            if SPY in self.gmwidg.gamemodel.spectators:
                self.advisors.append(EngineAdvisor(self.store, self.gmwidg.gamemodel.spectators[SPY], INVERSE_ANALYZING))
            self.gmwidg = None
# End of HACK
        board.bluearrow = None
        
        if legalMoveCount(board.model.getBoardAtPly(shown)) == 0:
            if self.sw.get_child() == self.tv:
                self.sw.remove(self.tv)
                label = gtk.Label(_("In this position,\nthere is no legal move."))
                label.set_property("yalign",0.1)
                self.sw.add_with_viewport(label)
                self.sw.get_child().set_shadow_type(gtk.SHADOW_NONE)
                self.sw.show_all()
            return
        
        for advisor in self.advisors:
            advisor.shown_changed(board, shown)
        self.tv.expand_all()
        
        if self.sw.get_child() != self.tv:
            self.sw.remove(self.sw.get_child())
            self.sw.add(self.tv)

    def selection_changed (self, widget, *args):
        iter = self.tv.get_selection().get_selected()[1]
        if iter:
            move = self.store[iter][0]
            if move:
                self.board.bluearrow = move.cords
                return
        self.board.bluearrow = None
    
    def row_activated (self, widget, *args):
        iter = self.tv.get_selection().get_selected()[1]
        if iter is None:
            return
        move = self.store[iter][0]
        if move:
            # Play the move if it's a suggestion for the next move of the game.
            b = self.board.model.boards[-1]
            if self.board.model.ply != self.board.shown: return
            if b[move.cords[0]].color != b.color: return
            self.board.bluearrow = None
            self.boardcontrol.emit("piece_moved", move, b.color)
        else:
            # The row may be tied to a specific action.
            path = self.store.get_path(iter)
            self.advisors[path[0]].row_activated(path)
    
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
        if not path:
            return False
        treeview.set_tooltip_row(tooltip, path)
        
        # And ask the advisor for some text
        iter = self.store.get_iter(path)
        text = self.advisors[path[0]].query_tooltip(path)
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

import gtk, gobject, cairo, pango

from pychess.System import conf
from pychess.Utils.const import *
from pychess.Utils.book import getOpenings
from pychess.Utils.eco import get_eco
from pychess.Utils.logic import legalMoveCount
from pychess.Utils.EndgameTable import EndgameTable
from pychess.Utils.Move import Move, toSAN, toFAN, parseAny, listToSan
from pychess.Utils.lutils.ldata import MATE_VALUE
from pychess.System.prefix import addDataPrefix


__title__ = _("Hints")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _("The hint panel will provide computer advice during each stage of the game")

__about__ = _("Official PyChess panel.")


class Advisor:
    def __init__ (self, store, name):
        """ The tree store's columns are:
            (Board, Move, pv)           Indicate the suggested move
            (text, barWidth, goodness)  Indicate its strength (last 2 are 0 to 1.0)
            pvlines                     Number of analysis lines for analysing engines
            is_pvlines_editable         Boolean
            Details                     Describe a PV, opening name, etc. """

        self.store = store
        iter = store.append(None, self.textOnlyRow(name))
        self.path = store.get_path(iter)
    
    def shown_changed (self, boardview, shown):
        """ Update the suggestions to match a changed position. """
        pass
    
    def child_tooltip (self, i):
        """ Return a tooltip (or empty) string for the given child row. """
        return ""
    
    def row_activated (self, path, model):
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
            self.store.remove(child)

    def textOnlyRow(self, text):
        return [(None, None, None), ("", 0, None), 0, False, text]

    def edited(self, path):
        pass


class OpeningAdvisor(Advisor):
    def __init__ (self, store):
        Advisor.__init__(self, store, _("Opening Book"))
        self.tooltip = _("The opening book will try to inspire you during the opening phase of the game by showing you common moves made by chess masters")
        self.opening_names = []
        
    def shown_changed (self, boardview, shown):
        m = boardview.model
        b = m.getBoardAtPly(shown, boardview.variation)
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

        self.opening_names = []
        for move, weight, games, score in openings:
            if totalWeight != 0:
                weight /= totalWeight
            goodness = min(weight * len(openings), 1.0)
            weight = "%0.1f%%" % (100 * weight)
            
            opening = get_eco(b.move(Move(move)).board.hash)
            if opening is None:
                eco = ""
                self.opening_names.append("")
            else:
                eco = opening[0]
                self.opening_names.append("%s %s" % (opening[1], opening[2]))

            self.store.append(parent, [(b, Move(move), None), (weight, 1, goodness), 0, False, eco])
    
    def child_tooltip (self, i):
        return "" if len(self.opening_names)==0 else self.opening_names[i]


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
        engineMax = self.engine.maxAnalysisLines()
        self.linesExpected   = min(conf.get("multipv", 1), engineMax)
        self.linesMax        = 1
        
        parent = self.empty_parent()
        self.store.append(parent, self.textOnlyRow(_("Calculating...")))
        
        # set pvlines, but set it 0 if engine max is only 1
        self.store.set_value(parent, 2, 0 if engineMax==1 else self.linesExpected)
        # set it editable
        self.store.set_value(parent, 3, engineMax>1)
        self.connection = engine.connect("analyze", self.on_analyze)
    
    def __del__ (self):
        self.engine.disconnect(self.connection)
    
    def shown_changed (self, boardview, shown):
        self.engine.setBoard(boardview.model.getBoardAtPly(shown, boardview.variation))
        
        parent = self.empty_parent()
        for line in xrange(self.linesExpected):
            self.store.append(parent, self.textOnlyRow(_("Calculating...")))

        self.linesMax = min(self.engine.maxAnalysisLines(), legalMoveCount(self.engine.board))
        self.active = True
    
    def on_analyze (self, engine, analysis):
        if not self.active:
            return

        for i, line in enumerate(analysis):
            if line is None:
                break
            pv, score = line
            move = None
            if pv:
                move = pv[0]

            board0 = self.engine.board
            board = board0.clone()
            ply0 = board.ply if self.mode == ANALYZING else board.ply+1
            counted_pv = []
            for j, pvmove in enumerate(pv):
                ply = ply0 + j
                if ply % 2 == 0:
                    mvcount = "%d." % (ply/2+1)
                elif j==0:
                    mvcount = "%d..." % (ply/2+1)
                else:
                    mvcount = ""
                counted_pv.append("%s%s" % (mvcount, toSAN(board, pvmove)))
                board = board.move(pvmove)

            # TODO make a move's "goodness" relative to other moves or past scores
            goodness = (min(max(score, -250), 250) + 250) / 500.0
            if self.engine.board.color == BLACK:
                score = -score
            self.store[self.path + (i,)] = [(board0, move, pv), (self.prettyPrintScore(score), 1, goodness), 0, False, " ".join(counted_pv)]
        
    def multipv_edited(self, value):
        if value > self.engine.maxAnalysisLines():
            return

        if value != self.linesExpected:
            self.engine.requestMultiPV(value)
            parent = self.store.get_iter(self.path)
            if value > self.linesExpected:
                while self.linesExpected < value:
                    self.store.append(parent, self.textOnlyRow(_("Calculating...")))
                    self.linesExpected += 1
            else:
                while self.linesExpected > value:
                    child = self.store.iter_children(parent)
                    self.store.remove(child)
                    self.linesExpected -= 1
        
    def row_activated (self, iter, model):
        if self.mode == ANALYZING and self.store.get_path(iter) != self.path:
            moves = self.store[iter][0][2]
            if moves is not None:
                model.add_variation(self.engine.board, moves)

    def child_tooltip (self, i):
        if self.active:
            if i < self.linesExpected:
                return _("Engine scores are in units of pawns, from White's point of view.")
            else:
                return _("Adding suggestions can help you find ideas, but slows down the computer's analysis.")
        return ""

    def prettyPrintScore (self, s):
        if s is None: return "?"
        if s == 0: return "0.00"
        if s > 0:
           pp = "+"
        else:
            pp = "-"
            s = -s
        
        if abs(s) == MATE_VALUE:
            return pp + "#%s" % MATE_VALUE
        else:
            return pp + "%0.2f" % (s / 100.0)


class EndgameAdvisor(Advisor):
    def __init__ (self, store):
        Advisor.__init__(self, store, _("Endgame Table"))
        self.egtb = EndgameTable()
        self.tooltip = _("The endgame table will show exact analysis when there are few pieces on the board.")
        # TODO: Show a message if tablebases for the position exist but are neither installed nor allowed.
    
    def shown_changed (self, boardview, shown):
        m = boardview.model
        b = m.getBoardAtPly(shown, boardview.variation)
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
            self.store.append(parent, [(b, move, None), result, 0, False, details])


class Sidepanel:
    def load (self, gmwidg):
        self.boardcontrol = gmwidg.board
        self.boardview = self.boardcontrol.view
        
        widgets = gtk.glade.XML(addDataPrefix("sidepanel/book.glade"))
        self.tv = widgets.get_widget("treeview")
        self.sw = widgets.get_widget("scrolledwindow")
        self.sw.unparent()
        self.store = gtk.TreeStore(gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, int, bool, str)
        self.tv.set_model(self.store)
        
        moveRenderer = gtk.CellRendererText()
        c0 = gtk.TreeViewColumn("Move", moveRenderer)

        def getMoveText(column, cell, store, iter):
            board, move, pv = store[iter][0]
            if not move:
                cell.set_property("text", "")
            else:
                if conf.get("figuresInNotation", False):
                    cell.set_property("text", toFAN(board, move))
                else:
                    cell.set_property("text", toSAN(board, move, True))
        c0.set_cell_data_func(moveRenderer, getMoveText)

        c1 = gtk.TreeViewColumn("Strength", StrengthCellRenderer(), data=1)

        multipvRenderer = gtk.CellRendererSpin()
        adjustment = gtk.Adjustment(value=conf.get("multipv", 1), lower=1, upper=9, step_incr=1)
        multipvRenderer.set_property("adjustment", adjustment)
        multipvRenderer.set_property("editable", True)
        multipvRenderer.set_property("width_chars", 3)
        c2 = gtk.TreeViewColumn("PV", multipvRenderer, editable=3)

        def currentCell(column, cell, store, iter):
            if store[iter][2] == 0:
                cell.set_property('visible', False)
            else:
                cell.set_property("text", store[iter][2])
                cell.set_property('visible', True)
        c2.set_cell_data_func(multipvRenderer, currentCell)

        def multipv_edited(renderer, path, text):
            iter = self.store.get_iter(path)
            self.store.set_value(iter, 2, int(text))
            self.advisors[int(path[0])].multipv_edited(int(text))
        multipvRenderer.connect('edited', multipv_edited)

        c3 = gtk.TreeViewColumn("Details", gtk.CellRendererText(), text=4)
        
        self.tv.append_column(c0)
        self.tv.append_column(c1)
        self.tv.append_column(c2)
        self.tv.append_column(c3)
        
        self.boardview.connect("shown_changed", self.shown_changed)
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
        self.shown_changed(self.boardview, 0)
        self.gmwidg = gmwidg # HACK
        
        return self.sw
    
    def shown_changed (self, boardview, shown):
# HACK
        if self.gmwidg:
            if HINT in self.gmwidg.gamemodel.spectators:
                self.advisors.append(EngineAdvisor(self.store, self.gmwidg.gamemodel.spectators[HINT], ANALYZING))
            if SPY in self.gmwidg.gamemodel.spectators:
                self.advisors.append(EngineAdvisor(self.store, self.gmwidg.gamemodel.spectators[SPY], INVERSE_ANALYZING))
            self.gmwidg = None
# End of HACK
        boardview.bluearrow = None
        
        if legalMoveCount(boardview.model.getBoardAtPly(shown, boardview.variation)) == 0:
            if self.sw.get_child() == self.tv:
                self.sw.remove(self.tv)
                label = gtk.Label(_("In this position,\nthere is no legal move."))
                label.set_property("yalign",0.1)
                self.sw.add_with_viewport(label)
                self.sw.get_child().set_shadow_type(gtk.SHADOW_NONE)
                self.sw.show_all()
            return
        
        for advisor in self.advisors:
            advisor.shown_changed(boardview, shown)
        self.tv.expand_all()
        
        if self.sw.get_child() != self.tv:
            self.sw.remove(self.sw.get_child())
            self.sw.add(self.tv)

    def selection_changed (self, widget, *args):
        iter = self.tv.get_selection().get_selected()[1]
        if iter:
            board, move, pv = self.store[iter][0]
            if move is not None:
                self.boardview.bluearrow = move.cords
                return
        self.boardview.bluearrow = None
    
    def row_activated (self, widget, *args):
        iter = self.tv.get_selection().get_selected()[1]
        if iter is None:
            return
        board, move, pv = self.store[iter][0]
        if (move is not None) and board == self.boardview.model.boards[-1]:
            # Play the move if it's a suggestion for the next move of the game.
            self.boardview.bluearrow = None
            self.boardcontrol.emit("piece_moved", move, board.color)
        else:
            # The row may be tied to a specific action.
            path = self.store.get_path(iter)
            self.advisors[path[0]].row_activated(iter, self.boardview.model)
    
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
            cairo.rel_move_to( 70 - w, (height - h) / 2)
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

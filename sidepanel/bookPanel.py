import os

from gi.repository import Gdk, Gtk, GObject, Pango, PangoCairo
from threading import Thread

from pychess.compat import Queue, Full
from pychess.System import conf, fident, uistuff
from pychess.Utils import prettyPrintScore
from pychess.Utils.const import *
from pychess.Utils.book import getOpenings
from pychess.Utils.eco import get_eco
from pychess.Utils.logic import legalMoveCount
from pychess.Utils.EndgameTable import EndgameTable
from pychess.Utils.Move import Move, toSAN, toFAN, listToMoves
from pychess.Utils.lutils.lmovegen import newMove
from pychess.Utils.lutils.lmove import ParsingError
from pychess.System.prefix import addDataPrefix
from pychess.System.Log import log
from pychess.System.idle_add import idle_add

__title__ = _("Hints")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _("The hint panel will provide computer advice during each stage of the game")

__about__ = _("Official PyChess panel.")


class Advisor (object):
    def __init__ (self, store, name, mode):
        """ The tree store's columns are:
            (Board, Move, pv)           Indicate the suggested move
            text or barWidth or goodness  Indicate its strength (last 2 are 0 to 1.0)
            pvlines                     Number of analysis lines for analysing engines
            is pvlines editable         Boolean
            Details                     Describe a PV, opening name, etc.
            star/stop                   Boolean HINT, SPY analyzing toggle button state
            is start/stop visible       Boolean """

        self.store = store
        self.name = name
        self.mode = mode
        store.append(None, self.textOnlyRow(name, mode))

    @property
    def path(self):
        for i, row in enumerate(self.store):
            if row[4] == self.name:
                return (i,)
    
    def shown_changed (self, boardview, shown):
        """ Update the suggestions to match a changed position. """
        pass

    def gamewidget_closed (self, gamewidget):
        pass
    
    def child_tooltip (self, i):
        """ Return a tooltip (or empty) string for the given child row. """
        return ""
    
    def row_activated (self, path, model):
        """ Act on a double-clicked child row other than a move suggestion. """
        pass
    
    def query_tooltip (self, path):
        indices = path.get_indices()
        if not indices[1:]:
            return self.tooltip
        return self.child_tooltip(indices[1])
    
    def empty_parent (self):
        while True:
            parent = self.store.get_iter(self.path)
            child = self.store.iter_children(parent)
            if not child:
                return parent
            self.store.remove(child)

    def textOnlyRow(self, text, mode=None):
        return [(None, None, None), ("", 0, None), 0, False, text, False, mode in (HINT, SPY)]


class OpeningAdvisor(Advisor):
    def __init__ (self, store, tv):
        Advisor.__init__(self, store, _("Opening Book"), OPENING)
        self.tooltip = _("The opening book will try to inspire you during the opening phase of the game by showing you common moves made by chess masters")
#        self.opening_names = []
        self.tv = tv
        
    def shown_changed (self, boardview, shown):
        m = boardview.model
        if m.isPlayingICSGame():
            return
        
        b = m.getBoardAtPly(shown, boardview.shownVariationIdx)
        parent = self.empty_parent()
        
        openings = getOpenings(b.board)
        openings.sort(key=lambda t: t[1], reverse=True)
        if not openings:
            return
        
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
#                self.opening_names.append("")
            else:
                eco = "%s - %s %s" % (opening[0], opening[1], opening[2])
#                self.opening_names.append("%s %s" % (opening[1], opening[2]))

            self.store.append(parent, [(b, Move(move), None), (weight, 1, goodness), 0, False, eco, False, False])        
        tp = Gtk.TreePath(self.path)        
        self.tv.expand_row(tp, False)
    
#    def child_tooltip (self, i):
#        return "" if len(self.opening_names)==0 else self.opening_names[i]


class EngineAdvisor(Advisor):
    # An EngineAdvisor always has self.linesExpected rows reserved for analysis.
    def __init__ (self, store, engine, mode, tv, boardview):
        if mode == HINT:
            Advisor.__init__(self, store, _("Analysis by %s") % engine, HINT)
            self.tooltip = _("%s will try to predict which move is best and which side has the advantage") % engine
        else:
            Advisor.__init__(self, store, _("Threat analysis by %s") % engine, SPY)
            self.tooltip = _("%s will identify what threats would exist if it were your opponent's turn to move") % engine
        self.engine = engine
        self.tv = tv
        self.active = False
        self.linesExpected   = 1
        self.boardview = boardview
        
        self.connection = engine.connect("analyze", self.on_analyze)
        engine.connect("readyForOptions", self.on_ready_for_options)
    
    def _del (self):
        self.engine.disconnect(self.connection)
    
    def _create_new_expected_lines(self):
        parent = self.empty_parent()
        for line in range(self.linesExpected):
            self.store.append(parent, self.textOnlyRow(_("Calculating...")))
        self.tv.expand_row(Gtk.TreePath(self.path), False)
        return parent
    
    def shown_changed (self, boardview, shown):
        m = boardview.model
        if m.isPlayingICSGame():
            return

        if not self.active:
            return
        
        self.engine.setBoard(boardview.model.getBoardAtPly(shown, boardview.shownVariationIdx))
        self._create_new_expected_lines()
        
    def on_ready_for_options (self, engine):
        engineMax = self.engine.maxAnalysisLines()
        self.linesExpected   = min(conf.get("multipv", 1), engineMax)

        m = self.boardview.model
        if m.isPlayingICSGame():
            return

        parent = self._create_new_expected_lines()

        # set pvlines, but set it 0 if engine max is only 1
        self.store.set_value(parent, 2, 0 if engineMax==1 else self.linesExpected)
        # set it editable
        self.store.set_value(parent, 3, engineMax>1)
        # set start/stop cb visible
        self.store.set_value(parent, 6, True)
        self.active = True
        
        self.shown_changed(self.boardview, self.boardview.shown)
    
    @idle_add
    def on_analyze (self, engine, analysis):
        if self.boardview.animating:
            return
            
        m = self.boardview.model
        if m.isPlayingICSGame():
            return

        if not self.active:
            return

        is_FAN = conf.get("figuresInNotation", False)
        
        for i, line in enumerate(analysis):
            if line is None:
                self.store[self.path + (i,)] = self.textOnlyRow("")
                continue

            board0 = self.engine.board
            board = board0.clone()
                
            movstrs, score, depth = line
            try:
                pv = listToMoves(board, movstrs, validate=True)
            except ParsingError as e:
                # ParsingErrors may happen when parsing "old" lines from
                # analyzing engines, which haven't yet noticed their new tasks
                log.debug("__parseLine: Ignored (%s) from analyzer: ParsingError%s" % \
                    (' '.join(movstrs),e))
                return
            except:
                return

            move = None
            if pv:
                move = pv[0]

            ply0 = board.ply if self.mode == HINT else board.ply+1
            counted_pv = []
            for j, pvmove in enumerate(pv):
                ply = ply0 + j
                if ply % 2 == 0:
                    mvcount = "%d." % (ply/2+1)
                elif j==0:
                    mvcount = "%d..." % (ply/2+1)
                else:
                    mvcount = ""
                counted_pv.append("%s%s" % (mvcount, toFAN(board, pvmove) if is_FAN else toSAN(board, pvmove, True)))
                board = board.move(pvmove)

            # TODO make a move's "goodness" relative to other moves or past scores
            goodness = (min(max(score, -250), 250) + 250) / 500.0
            if self.engine.board.color == BLACK:
                score = -score
            
            self.store[self.path + (i,)] = [(board0, move, pv), (prettyPrintScore(score, depth), 1, goodness), 0, False, " ".join(counted_pv), False, False]
    
    def start_stop(self, tb):
        if not tb:
            self.active = True
            self.boardview.model.resume_analyzer(self.mode)
            self.shown_changed(self.boardview, self.boardview.shown)
        else:
            self.active = False
            self.boardview.model.pause_analyzer(self.mode)
        
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
                    if child is not None:
                        self.store.remove(child)
                    self.linesExpected -= 1
        
    def row_activated (self, iter, model):
        if self.mode == HINT and self.store.get_path(iter) != Gtk.TreePath(self.path):
            moves = self.store[iter][0][2]
            if moves is not None:
                score = self.store[iter][1][0]
                model.add_variation(self.engine.board, moves, comment="", score=score)
                
        if self.mode == SPY and self.store.get_path(iter) != Gtk.TreePath(self.path):
            moves = self.store[iter][0][2]
            if moves is not None:
                score = self.store[iter][1][0]
                board = self.engine.board.board
                # SPY analyzer has inverted color boards
                # we need to chage it to get the board in gamemodel variations board list later
                board.setColor(1-board.color)
                king = board.kings[board.color]
                null_move = Move(newMove(king, king, NULL_MOVE))
                model.add_variation(self.engine.board, [null_move] + moves, comment="", score=score)

    def child_tooltip (self, i):
        if self.active:
            if i < self.linesExpected:
                return _("Engine scores are in units of pawns, from White's point of view. Double clicking on analysis lines you can insert them into Annotation panel as variations.")
            else:
                return _("Adding suggestions can help you find ideas, but slows down the computer's analysis.")
        return ""


class EndgameAdvisor(Advisor, Thread):
    def __init__ (self, store, tv, boardview):
        Thread.__init__(self, name=fident(self.run))
        self.daemon = True
        # FIXME 'Advisor.name = ...' in Advisor.__init__ overwrites Thread.name
        Advisor.__init__(self, store, _("Endgame Table"), ENDGAME)
        self.egtb = EndgameTable()
        self.tv = tv
        self.boardview = boardview
        self.tooltip = _("The endgame table will show exact analysis when there are few pieces on the board.")
        # TODO: Show a message if tablebases for the position exist but are neither installed nor allowed.

        self.egtb.connect("scored", self.on_scored)
        self.queue = Queue()
        self.start()
        
    class StopNow (Exception): pass

    def run (self):
        while True:
            v = self.queue.get()
            if v == self.StopNow:
                break
            elif v == self.board.board:
                self.egtb.scoreAllMoves(v)
            self.queue.task_done()

    def shown_changed (self, boardview, shown):
        m = boardview.model
        if m.isPlayingICSGame():
            return

        self.parent = self.empty_parent()
        self.board = m.getBoardAtPly(shown, boardview.shownVariationIdx)
        self.queue.put(self.board.board)

    def gamewidget_closed (self, gamewidget):
        try:
            self.queue.put_nowait(self.StopNow)
        except Full:
            log.warning("EndgameAdvisor.gamewidget_closed: Queue.Full")

    @idle_add
    def on_scored(self, w, ret):
        m = self.boardview.model
        if m.isPlayingICSGame():
            return

        board, endings = ret
        if board != self.board.board:
            return

        for move, result, depth in endings:
            if result == DRAW:
                result = (_("Draw"), 1, 0.5)
                details = ""
            elif (result == WHITEWON) ^ (self.board.color == WHITE):
                result = (_("Loss"), 1, 0.0)
                details = _("Mate in %d") % depth
            else:
                result = (_("Win"), 1, 1.0)
                details = _("Mate in %d") % depth
            self.store.append(self.parent, [(self.board, move, None), result, 0, False, details, False, False])
        self.tv.expand_row(Gtk.TreePath(self.path), False)

class Sidepanel (object):
    def load (self, gmwidg):
        self.boardcontrol = gmwidg.board
        self.boardview = self.boardcontrol.view
        
        widgets = Gtk.Builder()
        widgets.add_from_file(addDataPrefix("sidepanel/book.glade"))
        self.tv = widgets.get_object("treeview")
        self.sw = widgets.get_object("scrolledwindow")
        self.sw.unparent()
        self.store = Gtk.TreeStore(GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT, int, bool, str, bool, bool)
        self.tv.set_model(self.store)
        
        ### move suggested
        moveRenderer = Gtk.CellRendererText()
        moveRenderer.set_property("xalign", 1.0)
        moveRenderer.set_property("yalign", 0)
        c0 = Gtk.TreeViewColumn("Move", moveRenderer)

        def getMoveText(column, cell, store, iter, data):
            board, move, pv = store[iter][0]
            if not move:
                cell.set_property("text", "")
            else:
                if conf.get("figuresInNotation", False):
                    cell.set_property("text", toFAN(board, move))
                else:
                    cell.set_property("text", toSAN(board, move, True))
        c0.set_cell_data_func(moveRenderer, getMoveText)

        ### strength of the move       
        c1 = Gtk.TreeViewColumn("Strength", StrengthCellRenderer(), data=1)       

        ### multipv (number of analysis lines)
        multipvRenderer = Gtk.CellRendererSpin()
        adjustment = Gtk.Adjustment(value=conf.get("multipv", 1), lower=1, upper=9, step_incr=1)
        multipvRenderer.set_property("adjustment", adjustment)
        multipvRenderer.set_property("editable", True)
        multipvRenderer.set_property("width_chars", 1)
        c2 = Gtk.TreeViewColumn("PV", multipvRenderer, editable=3)
        c2.set_property("min_width", 80)

        def spin_visible(column, cell, store, iter, data):           
            if store[iter][2] == 0:
                cell.set_property('visible', False)
            else:
                cell.set_property("text", str(store[iter][2]))
                cell.set_property('visible', True)
        c2.set_cell_data_func(multipvRenderer, spin_visible)

        def multipv_edited(renderer, path, text):
            iter = self.store.get_iter(path)
            self.store.set_value(iter, 2, int(text))
            self.advisors[int(path[0])].multipv_edited(int(text))
        multipvRenderer.connect('edited', multipv_edited)

        ### start/stop button for analysis engines
        toggleRenderer = CellRendererPixbufXt()
        toggleRenderer.set_property("stock-id", "gtk-add")
        c4 = Gtk.TreeViewColumn("StartStop", toggleRenderer)

        def cb_visible(column, cell, store, iter, data):
            if not store[iter][6]:
                cell.set_property('visible', False)
            else:
                cell.set_property('visible', True)
            
            if store[iter][5]:
                cell.set_property("stock-id", "gtk-add")
            else:
                cell.set_property("stock-id", "gtk-remove")
        c4.set_cell_data_func(toggleRenderer, cb_visible)

        def toggled_cb(cell, path):
            self.store[path][5] = not self.store[path][5]
            self.advisors[int(path[0])].start_stop(self.store[path][5])
        toggleRenderer.connect('clicked', toggled_cb)

        self.tv.append_column(c4)
        self.tv.append_column(c0)
        self.tv.append_column(c1)
        self.tv.append_column(c2)
        ### header text, or analysis line
        uistuff.appendAutowrapColumn(self.tv, "Details", text=4)
        
        self.boardview.connect("shown_changed", self.shown_changed)
        self.tv.connect("cursor_changed", self.selection_changed)
        self.tv.connect("select_cursor_row", self.selection_changed)
        self.tv.connect("row-activated", self.row_activated)
        self.tv.connect("query-tooltip", self.query_tooltip)
        
        self.tv.props.has_tooltip = True
        self.tv.set_property("show-expanders", False)
        
        self.advisors = []

        if conf.get("opening_check", 0):
            self.advisors.append(OpeningAdvisor(self.store, self.tv))
        if conf.get("endgame_check", 0):
            advisor = EndgameAdvisor(self.store, self.tv, self.boardview)
            self.advisors.append(advisor)
            gmwidg.connect("closed", advisor.gamewidget_closed)
            
        gmwidg.gamemodel.connect("analyzer_added", self.on_analyzer_added)
        gmwidg.gamemodel.connect("analyzer_removed", self.on_analyzer_removed)
        gmwidg.gamemodel.connect("analyzer_paused", self.on_analyzer_paused)
        gmwidg.gamemodel.connect("analyzer_resumed", self.on_analyzer_resumed)
        
        def on_opening_check(none):
            if conf.get("opening_check", 0):
                advisor = OpeningAdvisor(self.store, self.tv)
                self.advisors.append(advisor)
                advisor.shown_changed(self.boardview, self.boardview.shown)
            else:
                for advisor in self.advisors:
                    if advisor.mode == OPENING:
                        parent = advisor.empty_parent()
                        self.store.remove(parent)
                        self.advisors.remove(advisor)
        conf.notify_add("opening_check", on_opening_check)

        def on_opening_file_entry_changed(none):
            default_path = os.path.join(addDataPrefix("pychess_book.bin"))
            path = conf.get("opening_file_entry", default_path) 
            if os.path.isfile(path):
                for advisor in self.advisors:
                    if advisor.mode == OPENING:
                        advisor.shown_changed(self.boardview, self.boardview.shown)
        conf.notify_add("opening_file_entry", on_opening_file_entry_changed)

        def on_endgame_check(none):
            if conf.get("endgame_check", 0):
                advisor = EndgameAdvisor(self.store, self.tv, self.boardview)
                self.advisors.append(advisor)
                advisor.shown_changed(self.boardview, self.boardview.shown)
                gmwidg.connect("closed", advisor.gamewidget_closed)
            else:
                for advisor in self.advisors:
                    if advisor.mode == ENDGAME:
                        advisor.gamewidget_closed(gmwidg)
                        parent = advisor.empty_parent()
                        self.store.remove(parent)
                        self.advisors.remove(advisor)
        conf.notify_add("endgame_check", on_endgame_check)

        return self.sw

    
    def on_analyzer_added(self, gamemodel, analyzer, analyzer_type):
        if analyzer_type == HINT:
            self.advisors.append(EngineAdvisor(self.store, analyzer, HINT, self.tv, self.boardview))
        if analyzer_type == SPY:
            self.advisors.append(EngineAdvisor(self.store, analyzer, SPY, self.tv, self.boardview))

    def on_analyzer_removed(self, gamemodel, analyzer, analyzer_type):
        for advisor in self.advisors:
            if advisor.mode == analyzer_type:
                advisor.active = False
                parent = advisor.empty_parent()
                self.store.remove(parent)
                self.advisors.remove(advisor)

    def on_analyzer_paused(self, gamemodel, analyzer, analyzer_type):
        for advisor in self.advisors:
            if advisor.mode == analyzer_type:
                advisor.active = False
                self.store[advisor.path][5] = True
                advisor.empty_parent()

    def on_analyzer_resumed(self, gamemodel, analyzer, analyzer_type):
        for advisor in self.advisors:
            if advisor.mode == analyzer_type:
                self.store[advisor.path][5] = False
                advisor.active = True
                advisor.shown_changed(self.boardview, self.boardview.shown)

    @idle_add
    def shown_changed (self, boardview, shown):
        boardview.bluearrow = None
        
        if legalMoveCount(boardview.model.getBoardAtPly(shown, boardview.shownVariationIdx)) == 0:
            if self.sw.get_child() == self.tv:
                self.sw.remove(self.tv)
                label = Gtk.Label(_("In this position,\nthere is no legal move."))
                label.set_property("yalign",0.1)
                self.sw.add_with_viewport(label)
                self.sw.get_child().set_shadow_type(Gtk.ShadowType.NONE)
                self.sw.show_all()
            return
        
        for advisor in self.advisors:
            advisor.shown_changed(boardview, shown)
        self.tv.expand_all()
        
        if self.sw.get_child() != self.tv:
            log.warning("bookPanel.Sidepanel.shown_changed: get_child() != tv")
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
        # The row may be tied to a specific action.
        path = self.store.get_path(iter)
        indices = path.get_indices()
        if indices:
            self.advisors[indices[0]].row_activated(iter, self.boardview.model)
    
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
        indices = path.get_indices()
        if indices:
            text = self.advisors[indices[0]].query_tooltip(path)
            if text:
                tooltip.set_markup(text)
                return True # Show the tip.
            
        return False

################################################################################
# StrengthCellRenderer                                                         #
################################################################################

width, height = 80, 23
class StrengthCellRenderer (Gtk.CellRenderer):
    __gproperties__ = {
        "data": (GObject.TYPE_PYOBJECT, "Data", "Data", GObject.PARAM_READWRITE),
    }
    
    def __init__(self):
        Gtk.CellRenderer.__init__(self)
        self.data = None

    def do_set_property(self, pspec, value):        
        setattr(self, pspec.name, value)
        
    def do_get_property(self, pspec):      
        return getattr(self, pspec.name)
        
    def do_render(self, context, widget, background_area, cell_area, flags):      
        if not self.data: return
        text, widthfrac, goodness = self.data
        if widthfrac:
            paintGraph(context, widthfrac, stoplightColor(goodness), cell_area)
        if text:
            layout = PangoCairo.create_layout(context)
            layout.set_text(text, -1)

            fd = Pango.font_description_from_string ("Sans 10")
            layout.set_font_description(fd)
            
            w, h = layout.get_pixel_size()
            context.move_to (cell_area.x, cell_area.y)
            context.rel_move_to( 70 - w, (height - h) / 2)
            
            PangoCairo.show_layout(context, layout)      

    def do_get_size(self, widget, cell_area=None):       
        return (0, 0, width, height)

GObject.type_register(StrengthCellRenderer)

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

# cell renderer for start-stop putton
class CellRendererPixbufXt(Gtk.CellRendererPixbuf):
    __gproperties__ = { 'active-state' :                                      
                        (GObject.TYPE_STRING, 'pixmap/active widget state',  
                        'stock-icon name representing active widget state',  
                        None, GObject.PARAM_READWRITE) }                      
    __gsignals__    = { 'clicked' :                                          
                        (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_STRING,)) , } 

    def __init__( self ):                                                    
        GObject.GObject.__init__( self )                              
        self.set_property( 'mode', Gtk.CellRendererMode.ACTIVATABLE )      
                                                                              
    def do_get_property( self, property ):                                    
        if property.name == 'active-state':                                  
            return self.active_state                                          
        else:                                                                
            raise AttributeError('unknown property %s' % property.name)      
                                                                              
    def do_set_property( self, property, value ):                            
        if property.name == 'active-state':                                  
            self.active_state = value                                        
        else:                                                                
            raise AttributeError('unknown property %s' % property.name)      
                                                                              
    def do_activate( self, event, widget, path,  background_area, cell_area, flags ):    
        if event.type == Gdk.EventType.BUTTON_PRESS:                                
            self.emit('clicked', path)          
                                                  
    #def do_clicked(self, path):                                        
        #print "do_clicked", path                              
        
GObject.type_register(CellRendererPixbufXt)

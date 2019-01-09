import asyncio
import os

from gi.repository import Gdk, Gtk, GObject, Pango, PangoCairo

from pychess.compat import create_task
from pychess.System import conf, uistuff
from pychess.Utils import prettyPrintScore
from pychess.Utils.const import HINT, OPENING, SPY, BLACK, NULL_MOVE, ENDGAME, DRAW, WHITEWON, WHITE, NORMALCHESS
from pychess.Utils.book import getOpenings
from pychess.Utils.eco import get_eco
from pychess.Utils.logic import legalMoveCount
from pychess.Utils.Move import Move, toSAN, toFAN, listToMoves
from pychess.Utils.lutils.lmovegen import newMove
from pychess.Utils.lutils.lmove import ParsingError
from pychess.System.prefix import addDataPrefix
from pychess.System.Log import log
from math import ceil

__title__ = _("Hints")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _(
    "The hint panel will provide computer advice during each stage of the game")

__about__ = _("Official PyChess panel.")


class Advisor:
    def __init__(self, store, name, mode):
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
                return (i, )

    def shownChanged(self, boardview, shown):
        """ Update the suggestions to match a changed position. """
        pass

    def gamewidget_closed(self, gamewidget):
        pass

    def child_tooltip(self, i):
        """ Return a tooltip (or empty) string for the given child row. """
        return ""

    def row_activated(self, path, model):
        """ Act on a double-clicked child row other than a move suggestion. """
        pass

    def query_tooltip(self, path):
        indices = path.get_indices()
        if not indices[1:]:
            return self.tooltip
        return self.child_tooltip(indices[1])

    def empty_parent(self):
        while True:
            parent = self.store.get_iter(self.path)
            child = self.store.iter_children(parent)
            if not child:
                return parent
            self.store.remove(child)

    def textOnlyRow(self, text, mode=None):
        return [(None, None, None),
                ("", 0, None), 0, False, text, False, mode in (HINT, SPY)]

    def _del(self):
        pass


class OpeningAdvisor(Advisor):
    def __init__(self, store, tv, boardcontrol):
        Advisor.__init__(self, store, _("Opening Book"), OPENING)
        self.tooltip = _(
            "The opening book will try to inspire you during the opening phase of the game by showing you common moves made by chess masters")
        #        self.opening_names = []
        self.tv = tv
        self.boardcontrol = boardcontrol
        self.boardview = boardcontrol.view

    def shownChanged(self, boardview, shown):
        m = boardview.model
        if m is None or m.isPlayingICSGame():
            return

        b = m.getBoardAtPly(shown, boardview.shown_variation_idx)
        parent = self.empty_parent()

        openings = getOpenings(b.board)
        openings.sort(key=lambda t: t[1], reverse=True)
        if not openings:
            return

        totalWeight = 0.0
        # Polyglot-formatted books have space for learning data.
        # See version ac31dc37ec89 for an attempt to parse it.
        # In this version, we simply ignore it. (Most books don't have it.)
        for move, weight, learn in openings:
            totalWeight += weight

        self.opening_names = []
        for move, weight, learn in openings:
            if totalWeight != 0:
                weight /= totalWeight
            goodness = min(float(weight * len(openings)), 1.0)
            weight = "%0.1f%%" % (100 * weight)

            opening = get_eco(b.move(Move(move)).board.hash)
            if opening is None:
                eco = ""
#                self.opening_names.append("")
            else:
                eco = "%s - %s %s" % (opening[0], opening[1], opening[2])
#                self.opening_names.append("%s %s" % (opening[1], opening[2]))

            self.store.append(parent, [(b, Move(move), None), (
                weight, 1, goodness), 0, False, eco, False, False])
        tp = Gtk.TreePath(self.path)
        self.tv.expand_row(tp, False)

#    def child_tooltip (self, i):
#        return "" if len(self.opening_names)==0 else self.opening_names[i]

    def row_activated(self, iter, model, from_gui=True):
        if self.store.get_path(iter) != Gtk.TreePath(self.path):
            board, move, moves = self.store[iter][0]
            self.boardcontrol.play_or_add_move(board, move)


class EngineAdvisor(Advisor):
    # An EngineAdvisor always has self.linesExpected rows reserved for analysis.
    def __init__(self, store, engine, mode, tv, boardcontrol):
        if mode == HINT:
            Advisor.__init__(self, store, _("Analysis by %s") % engine, HINT)
            self.tooltip = _(
                "%s will try to predict which move is best and which side has the advantage") % engine
        else:
            Advisor.__init__(self, store, _("Threat analysis by %s") % engine,
                             SPY)
            self.tooltip = _(
                "%s will identify what threats would exist if it were your opponent's turn to move") % engine
        self.engine = engine
        self.tv = tv
        self.active = False
        self.linesExpected = 1
        self.boardview = boardcontrol.view

        self.cid1 = self.engine.connect("analyze", self.on_analyze)
        self.cid2 = self.engine.connect("readyForOptions", self.on_ready_for_options)
        self.cid3 = self.engine.connect_after("readyForMoves", self.on_ready_for_moves)

        self.figuresInNotation = conf.get("figuresInNotation")

        def on_figures_in_notation(none):
            self.figuresInNotation = conf.get("figuresInNotation")

        self.cid4 = conf.notify_add("figuresInNotation", on_figures_in_notation)

    def _del(self):
        self.engine.disconnect(self.cid1)
        self.engine.disconnect(self.cid2)
        self.engine.disconnect(self.cid3)
        conf.notify_remove(self.cid4)

    def _create_new_expected_lines(self):
        parent = self.empty_parent()
        for line in range(self.linesExpected):
            self.store.append(parent, self.textOnlyRow(_("Calculating...")))
        self.tv.expand_row(Gtk.TreePath(self.path), False)
        return parent

    def shownChanged(self, boardview, shown):
        m = boardview.model
        if m is None:
            return
        if m.isPlayingICSGame() and not m.lesson_game:
            return

        self.engine.setBoard(boardview.model.getBoardAtPly(
            shown, boardview.shown_variation_idx), search=self.active or m.lesson_game)

        if self.active:
            self._create_new_expected_lines()

    def on_ready_for_options(self, engine):
        engine_max = self.engine.maxAnalysisLines()
        engine_value = self.engine.getAnalysisLines()
        self.linesExpected = engine_value if engine_value <= engine_max else engine_max

        m = self.boardview.model
        if m.isPlayingICSGame():
            return

        parent = self._create_new_expected_lines()

        # set pvlines, but set it 0 if engine max is only 1
        self.store.set_value(parent, 2, 0 if engine_max == 1 else self.linesExpected)
        # set it editable
        self.store.set_value(parent, 3, engine_max > 1)
        # set start/stop cb visible
        self.store.set_value(parent, 6, True)
        self.active = True

    def on_ready_for_moves(self, engine):
        self.shownChanged(self.boardview, self.boardview.shown)

    def on_analyze(self, engine, analysis):
        if self.boardview.animating:
            return

        if self.boardview.model.isPlayingICSGame():
            return

        if not self.active:
            return

        for i, line in enumerate(analysis):
            if line is None:
                self.store[self.path + (i, )] = self.textOnlyRow("")
                continue

            ply, movstrs, score, depth, nps = line
            board0 = self.engine.board
            board = board0.clone()
            try:
                pv = listToMoves(board, movstrs, validate=True)
            except ParsingError as e:
                # ParsingErrors may happen when parsing "old" lines from
                # analyzing engines, which haven't yet noticed their new tasks
                log.debug("EngineAdvisor.on_analyze(): Ignored (%s) from analyzer: ParsingError%s" %
                          (' '.join(movstrs), e))
                return

            move = None
            if pv:
                move = pv[0]

            ply0 = board.ply if self.mode == HINT else board.ply + 1
            counted_pv = []
            for j, pvmove in enumerate(pv):
                ply = ply0 + j
                if ply % 2 == 0:
                    mvcount = "%d." % (ply / 2 + 1)
                elif j == 0:
                    mvcount = "%d..." % (ply / 2 + 1)
                else:
                    mvcount = ""
                counted_pv.append("%s%s" %
                                  (mvcount, toFAN(board, pvmove)
                                   if self.figuresInNotation else toSAN(board, pvmove, True)))
                board = board.move(pvmove)

            goodness = (min(max(score, -250), 250) + 250) / 500.0
            if self.engine.board.color == BLACK:
                score = -score

            self.store[self.path + (i, )] = [
                (board0, move, pv),
                (prettyPrintScore(score, depth, format_mate=True), 1, goodness), 0, False,
                " ".join(counted_pv), False, False
            ]

    def start_stop(self, tb):
        if not tb:
            self.active = True
            self.boardview.model.resume_analyzer(self.mode)
        else:
            self.active = False
            self.boardview.model.pause_analyzer(self.mode)

    def multipv_edited(self, value):
        value = self.engine.requestMultiPV(value)
        if value != self.linesExpected:
            parent = self.store.get_iter(self.path)
            if value > self.linesExpected:
                while self.linesExpected < value:
                    self.store.append(parent,
                                      self.textOnlyRow(_("Calculating...")))
                    self.linesExpected += 1
            else:
                while self.linesExpected > value:
                    child = self.store.iter_children(parent)
                    if child is not None:
                        self.store.remove(child)
                    self.linesExpected -= 1
        return value

    def row_activated(self, iter, model):
        if not self.active:
            return

        if self.mode == HINT and self.store.get_path(iter) != Gtk.TreePath(self.path):
            moves = self.store[iter][0][2]
            if moves is not None:
                # score = self.store[iter][1][0]
                model.add_variation(self.engine.board, moves)

        if self.mode == SPY and self.store.get_path(iter) != Gtk.TreePath(self.path):
            moves = self.store[iter][0][2]
            if moves is not None:
                # score = self.store[iter][1][0]
                board = self.engine.board.board
                # SPY analyzer has inverted color boards
                # we need to chage it to get the board in gamemodel variations board list later
                board.setColor(1 - board.color)
                king = board.kings[board.color]
                null_move = Move(newMove(king, king, NULL_MOVE))
                model.add_variation(self.engine.board, [null_move] + moves)

    def child_tooltip(self, i):
        if self.active:
            if i < self.linesExpected:
                return _(
                    "Engine scores are in units of pawns, from White's point of view. Double clicking on analysis lines you can insert them into Annotation panel as variations.")
            else:
                return _(
                    "Adding suggestions can help you find ideas, but slows down the computer's analysis.")
        return ""


class EndgameAdvisor(Advisor):
    def __init__(self, store, tv, boardcontrol):
        Advisor.__init__(self, store, _("Endgame Table"), ENDGAME)
        # deferred import to not slow down PyChess starting up
        from pychess.Utils.EndgameTable import EndgameTable
        self.egtb = EndgameTable()
        # If mate in # was activated by double click let egtb do the rest
        self.auto_activate = False
        self.tv = tv
        self.boardcontrol = boardcontrol
        self.boardview = boardcontrol.view
        self.tooltip = _(
            "The endgame table will show exact analysis when there are few pieces on the board.")
        # TODO: Show a message if tablebases for the position exist but are neither installed nor allowed.

        self.queue = asyncio.Queue()
        self.egtb_task = create_task(self.start())

    class StopNow(Exception):
        pass

    @asyncio.coroutine
    def start(self):
        while True:
            v = yield from self.queue.get()
            if isinstance(v, Exception) and v == self.StopNow:
                break
            elif v == self.board.board:
                ret = yield from self.egtb.scoreAllMoves(v)
                self.on_scored(v, ret)
            self.queue.task_done()

    def shownChanged(self, boardview, shown):
        m = boardview.model
        if m is None or m.variant.variant != NORMALCHESS or m.isPlayingICSGame():
            if not (m.practice_game or m.lesson_game):
                return

        self.parent = self.empty_parent()
        self.board = m.getBoardAtPly(shown, boardview.shown_variation_idx)
        self.queue.put_nowait(self.board.board)

    def _del(self):
        try:
            self.queue.put_nowait(self.StopNow)
        except asyncio.QueueFull:
            log.warning("EndgameAdvisor.gamewidget_closed: Queue.Full")
        self.egtb_task.cancel()

    def on_scored(self, board, endings):
        m = self.boardview.model

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

            if m.practice_game or m.lesson_game:
                m.hint = "%s %s %s" % (toSAN(self.board, move, True), result[0], details)
                return

            if m.isPlayingICSGame():
                return

            self.store.append(self.parent, [(self.board, move, None), result,
                                            0, False, details, False, False])

        self.tv.expand_row(Gtk.TreePath(self.path), False)

        if self.auto_activate:
            path = None
            for i, row in enumerate(self.store):
                if row[4] == self.name:
                    path = Gtk.TreePath.new_from_indices((i, 0))
                    break
            if path is not None:
                self.row_activated(self.tv.get_model().get_iter(path), m, from_gui=False)

    def row_activated(self, iter, model, from_gui=True):
        if self.store.get_path(iter) != Gtk.TreePath(self.path):
            board, move, moves = self.store[iter][0]

            if from_gui:
                result = self.store[iter][1]
                if result is not None and result[2] != 0.5:
                    # double click on mate in #
                    self.auto_activate = True

            self.boardcontrol.play_or_add_move(board, move)


class Sidepanel:
    def load(self, gmwidg):
        self.gmwidg = gmwidg
        self.boardcontrol = gmwidg.board
        self.boardview = gmwidg.board.view

        self.figuresInNotation = conf.get("figuresInNotation")

        self.sw = Gtk.ScrolledWindow()
        self.tv = Gtk.TreeView()
        self.tv.set_property("headers_visible", False)
        self.sw.add(self.tv)
        self.sw.show_all()

        self.store = Gtk.TreeStore(GObject.TYPE_PYOBJECT,
                                   GObject.TYPE_PYOBJECT, int, bool, str, bool,
                                   bool)
        self.tv.set_model(self.store)

        # ## move suggested
        moveRenderer = Gtk.CellRendererText()
        moveRenderer.set_property("xalign", 1.0)
        moveRenderer.set_property("yalign", 0)
        c0 = Gtk.TreeViewColumn("Move", moveRenderer)

        def getMoveText(column, cell, store, iter, data):
            board, move, pv = store[iter][0]
            if not move:
                cell.set_property("text", "")
            else:
                if self.figuresInNotation:
                    cell.set_property("text", toFAN(board, move))
                else:
                    cell.set_property("text", toSAN(board, move, True))

        c0.set_cell_data_func(moveRenderer, getMoveText)

        # ## strength of the move
        c1 = Gtk.TreeViewColumn("Strength", StrengthCellRenderer(), data=1)

        # ## multipv (number of analysis lines)
        self.multipvRenderer = Gtk.CellRendererSpin()
        adjustment = Gtk.Adjustment(value=1,
                                    lower=1,
                                    upper=9,
                                    step_increment=1)
        self.multipvRenderer.set_property("adjustment", adjustment)
        self.multipvRenderer.set_property("editable", True)
        self.multipvRenderer.set_property("width_chars", 1)
        c2 = Gtk.TreeViewColumn("PV", self.multipvRenderer, editable=3)
        c2.set_property("min_width", 80)

        def spin_visible(column, cell, store, iter, data):
            if store[iter][2] == 0:
                cell.set_property('visible', False)
            else:
                cell.set_property("text", str(store[iter][2]))
                cell.set_property('visible', True)

        c2.set_cell_data_func(self.multipvRenderer, spin_visible)

        def multipv_edited(renderer, path, text):
            iter = self.store.get_iter(path)
            self.store.set_value(iter, 2, self.advisors[int(path[0])].multipv_edited(1 if text == "" else int(text)))

        self.multipv_cid = self.multipvRenderer.connect('edited', multipv_edited)

        # ## start/stop button for analysis engines
        self.toggleRenderer = CellRendererPixbufXt()
        self.toggleRenderer.set_property("stock-id", "gtk-add")
        c4 = Gtk.TreeViewColumn("StartStop", self.toggleRenderer)

        def cb_visible(column, cell, store, iter, data):
            if not store[iter][6]:
                cell.set_property('visible', False)
            else:
                cell.set_property('visible', True)

            if store[iter][5]:
                cell.set_property("stock-id", "gtk-media-play")
            else:
                cell.set_property("stock-id", "gtk-media-pause")

        c4.set_cell_data_func(self.toggleRenderer, cb_visible)

        def toggled_cb(cell, path):
            self.store[path][5] = not self.store[path][5]
            self.advisors[int(path[0])].start_stop(self.store[path][5])

        self.toggle_cid = self.toggleRenderer.connect('clicked', toggled_cb)

        self.tv.append_column(c4)
        self.tv.append_column(c0)
        self.tv.append_column(c1)
        self.tv.append_column(c2)
        # ## header text, or analysis line
        uistuff.appendAutowrapColumn(self.tv, "Details", text=4)

        self.cid = self.boardview.connect("shownChanged", self.shownChanged)
        self.tv_cids = [
            self.tv.connect("cursor_changed", self.selection_changed),
            self.tv.connect("select_cursor_row", self.selection_changed),
            self.tv.connect("row-activated", self.row_activated),
            self.tv.connect("query-tooltip", self.query_tooltip),
        ]
        self.tv.props.has_tooltip = True
        self.tv.set_property("show-expanders", False)

        self.advisors = []
        self.conf_conids = []

        if conf.get("opening_check"):
            advisor = OpeningAdvisor(self.store, self.tv, self.boardcontrol)
            self.advisors.append(advisor)
        if conf.get("endgame_check"):
            advisor = EndgameAdvisor(self.store, self.tv, self.boardcontrol)
            self.advisors.append(advisor)

        self.model_cids = [
            gmwidg.gamemodel.connect("analyzer_added", self.on_analyzer_added),
            gmwidg.gamemodel.connect("analyzer_removed", self.on_analyzer_removed),
            gmwidg.gamemodel.connect_after("game_terminated", self.on_game_terminated),
        ]

        def on_opening_check(none):
            if conf.get("opening_check") and self.boardview is not None:
                advisor = OpeningAdvisor(self.store, self.tv, self.boardcontrol)
                self.advisors.append(advisor)
                advisor.shownChanged(self.boardview, self.boardview.shown)
            else:
                for advisor in self.advisors:
                    if advisor.mode == OPENING:
                        parent = advisor.empty_parent()
                        self.store.remove(parent)
                        self.advisors.remove(advisor)

        self.conf_conids.append(conf.notify_add("opening_check", on_opening_check))

        def on_opening_file_entry_changed(none):
            path = conf.get("opening_file_entry")
            if os.path.isfile(path):
                for advisor in self.advisors:
                    if advisor.mode == OPENING and self.boardview is not None:
                        advisor.shownChanged(self.boardview,
                                             self.boardview.shown)

        self.conf_conids.append(conf.notify_add("opening_file_entry", on_opening_file_entry_changed))

        def on_endgame_check(none):
            if conf.get("endgame_check"):
                advisor = EndgameAdvisor(self.store, self.tv, self.boardcontrol)
                self.advisors.append(advisor)
                advisor.shownChanged(self.boardview, self.boardview.shown)
            else:
                for advisor in self.advisors:
                    if advisor.mode == ENDGAME:
                        advisor._del()
                        parent = advisor.empty_parent()
                        self.store.remove(parent)
                        self.advisors.remove(advisor)

        self.conf_conids.append(conf.notify_add("endgame_check", on_endgame_check))

        def on_figures_in_notation(none):
            self.figuresInNotation = conf.get("figuresInNotation")

        self.conf_conids.append(conf.notify_add("figuresInNotation", on_figures_in_notation))

        return self.sw

    def on_game_terminated(self, model):
        self.multipvRenderer.disconnect(self.multipv_cid)
        self.toggleRenderer.disconnect(self.toggle_cid)
        for cid in self.tv_cids:
            self.tv.disconnect(cid)
        for conid in self.conf_conids:
            conf.notify_remove(conid)
        for cid in self.model_cids:
            self.gmwidg.gamemodel.disconnect(cid)
        self.boardview.disconnect(self.cid)
        for advisor in self.advisors:
            advisor._del()

    def on_analyzer_added(self, gamemodel, analyzer, analyzer_type):
        if analyzer_type == HINT:
            self.advisors.append(EngineAdvisor(self.store, analyzer, HINT,
                                               self.tv, self.boardcontrol))
        if analyzer_type == SPY:
            self.advisors.append(EngineAdvisor(self.store, analyzer, SPY,
                                               self.tv, self.boardcontrol))

    def on_analyzer_removed(self, gamemodel, analyzer, analyzer_type):
        for advisor in self.advisors:
            if advisor.mode == analyzer_type:
                advisor.active = False
                advisor.engine = None
                parent = advisor.empty_parent()
                self.store.remove(parent)
                self.advisors.remove(advisor)

    def shownChanged(self, boardview, shown):
        if boardview.model is None:
            return
        boardview.bluearrow = None

        if legalMoveCount(boardview.model.getBoardAtPly(
                shown, boardview.shown_variation_idx)) == 0:
            if self.sw.get_child() == self.tv:
                self.sw.remove(self.tv)
                label = Gtk.Label(_(
                    "In this position,\nthere is no legal move."))
                label.set_property("yalign", 0.1)
                self.sw.add_with_viewport(label)
                self.sw.get_child().set_shadow_type(Gtk.ShadowType.NONE)
                self.sw.show_all()

                # stop egtb auto activation on mating lines
                for advisor in self.advisors:
                    advisor.auto_activate = False
            return

        for advisor in self.advisors:
            advisor.shownChanged(boardview, shown)
        self.tv.expand_all()

        if self.sw.get_child() != self.tv:
            log.warning("bookPanel.Sidepanel.shownChanged: get_child() != tv")
            self.sw.remove(self.sw.get_child())
            self.sw.add(self.tv)

    def selection_changed(self, widget, *args):
        iter = self.tv.get_selection().get_selected()[1]
        if iter:
            board, move, pv = self.store[iter][0]
            if move is not None:
                self.boardview.bluearrow = move.cords
                return
        self.boardview.bluearrow = None

    def row_activated(self, widget, *args):
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
        path_col_x_y = treeview.get_path_at_pos(x, y)

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
                label = Gtk.Label()
                label.props.wrap = True
                label.props.width_chars = 60
                label.props.max_width_chars = 60
                label.set_text(text)
                tooltip.set_custom(label)
                # tooltip.set_markup(text)
                return True  # Show the tip.

        return False

################################################################################
# StrengthCellRenderer                                                         #
################################################################################


width, height = 80, 23


class StrengthCellRenderer(Gtk.CellRenderer):
    __gproperties__ = {
        "data":
        (GObject.TYPE_PYOBJECT, "Data", "Data", GObject.ParamFlags.READABLE | GObject.ParamFlags.WRITABLE),
    }

    def __init__(self):
        Gtk.CellRenderer.__init__(self)
        self.data = None

    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def do_render(self, context, widget, background_area, cell_area, flags):
        if not self.data:
            return
        text, widthfrac, goodness = self.data
        if widthfrac:
            paintGraph(context, widthfrac, stoplightColor(goodness), cell_area)
        if text:
            layout = PangoCairo.create_layout(context)
            layout.set_text(text, -1)

            fd = Pango.font_description_from_string("Sans 10")
            layout.set_font_description(fd)

            w, h = layout.get_pixel_size()
            context.move_to(cell_area.x, cell_area.y)
            context.rel_move_to(70 - w, (height - h) / 2)

            PangoCairo.show_layout(context, layout)

    def do_get_size(self, widget, cell_area=None):
        return (0, 0, width, height)


GObject.type_register(StrengthCellRenderer)

################################################################################
# StrengthCellRenderer functions                                               #
################################################################################


def stoplightColor(x):
    def interp(y0, yh, y1):
        return y0 + (y1 + 4 * yh - 3 * y0) * x + (-4 * yh + 2 * y0) * x * x
    r = interp(239, 252, 138) / 255
    g = interp(41, 233, 226) / 255
    b = interp(41, 79, 52) / 255
    return r, g, b


def paintGraph(cairo, widthfrac, rgb, rect):
    x, y, w0, h = rect.x, rect.y, rect.width, rect.height
    w = ceil(widthfrac * w0)

    cairo.save()
    cairo.rectangle(x, y, w, h)
    cairo.clip()
    cairo.move_to(x + 10, y)
    cairo.rel_line_to(w - 20, 0)
    cairo.rel_curve_to(10, 0, 10, 0, 10, 10)
    cairo.rel_line_to(0, 3)
    cairo.rel_curve_to(0, 10, 0, 10, -10, 10)
    cairo.rel_line_to(-w + 20, 0)
    cairo.rel_curve_to(-10, 0, -10, 0, -10, -10)
    cairo.rel_line_to(0, -3)
    cairo.rel_curve_to(0, -10, 0, -10, 10, -10)
    cairo.set_source_rgb(*rgb)
    cairo.fill()
    cairo.restore()


# cell renderer for start-stop putton
class CellRendererPixbufXt(Gtk.CellRendererPixbuf):
    __gproperties__ = {'active-state':
                       (GObject.TYPE_STRING, 'pixmap/active widget state',
                        'stock-icon name representing active widget state',
                        None, GObject.ParamFlags.READABLE | GObject.ParamFlags.WRITABLE)}
    __gsignals__ = {'clicked': (GObject.SignalFlags.RUN_LAST, None,
                                (GObject.TYPE_STRING, )), }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.set_property('mode', Gtk.CellRendererMode.ACTIVATABLE)

    def do_get_property(self, property):
        if property.name == 'active-state':
            return self.active_state
        else:
            raise AttributeError('unknown property %s' % property.name)

    def do_set_property(self, property, value):
        if property.name == 'active-state':
            self.active_state = value
        else:
            raise AttributeError('unknown property %s' % property.name)

    def do_activate(self, event, widget, path, background_area, cell_area,
                    flags):
        if event.type == Gdk.EventType.BUTTON_PRESS:
            self.emit('clicked', path)

    # def do_clicked(self, path):
    # print "do_clicked", path


GObject.type_register(CellRendererPixbufXt)

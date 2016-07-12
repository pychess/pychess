from __future__ import print_function
import sys
from math import e
from random import randint

from gi.repository import Gtk, GObject
from gi.repository import Gdk

from pychess.System import uistuff
from pychess.System.idle_add import idle_add
from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import WHITE, DRAW, WHITEWON, BLACKWON
from pychess.Utils.lutils import leval

__title__ = _("Score")

__icon__ = addDataPrefix("glade/panel_score.svg")

__desc__ = _(
    "The score panel tries to evaluate the positions and shows you a graph of the game progress")


class Sidepanel:
    def load(self, gmwidg):
        self.boardview = gmwidg.board.view
        self.plot = ScorePlot(self.boardview)
        self.sw = __widget__ = Gtk.ScrolledWindow()
        __widget__.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        port = Gtk.Viewport()
        port.add(self.plot)
        port.set_shadow_type(Gtk.ShadowType.NONE)
        __widget__.add(port)
        __widget__.show_all()

        self.plot_cid = self.plot.connect("selected", self.plot_selected)
        self.cid = self.boardview.connect('shownChanged', self.shownChanged)
        self.model_cids = [
            self.boardview.model.connect_after("game_changed", self.game_changed),
            self.boardview.model.connect_after("moves_undone", self.moves_undone),
            self.boardview.model.connect_after("analysis_changed", self.analysis_changed),
            self.boardview.model.connect_after("game_started", self.game_started),
            self.boardview.model.connect_after("game_terminated", self.on_game_terminated),
        ]
        uistuff.keepDown(__widget__)

        return __widget__

    def on_game_terminated(self, model):
        self.plot.disconnect(self.plot_cid)
        for cid in self.model_cids:
            self.boardview.model.disconnect(cid)
        self.boardview.disconnect(self.cid)

    def moves_undone(self, model, moves):
        for i in range(moves):
            self.plot.undo()

        # As shownChanged will normally be emitted just after game_changed -
        # if we are viewing the latest position - we can do the selection change
        # now, and thereby avoid redraw being called twice
        if self.plot.selected == model.ply - model.lowply:
            self.plot.select(model.ply - model.lowply - moves)
        self.plot.redraw()

    def game_changed(self, model, ply):
        if len(self.plot) + model.lowply > ply:
            return

        for i in range(len(self.plot) + model.lowply, ply):
            if i in model.scores:
                points = model.scores[i][1]
            else:
                points = leval.evaluateComplete(
                    model.getBoardAtPly(i).board, WHITE)
            self.plot.addScore(points)

        if model.status == DRAW:
            points = 0
        elif model.status == WHITEWON:
            points = sys.maxsize
        elif model.status == BLACKWON:
            points = -sys.maxsize
        else:
            if ply in model.scores:
                points = model.scores[ply][1]
            else:
                points = leval.evaluateComplete(
                    model.getBoardAtPly(ply).board, WHITE)
        self.plot.addScore(points)

        # As shownChanged will normally be emitted just after game_changed -
        # if we are viewing the latest position - we can do the selection change
        # now, and thereby avoid redraw being called twice
        if self.plot.selected == ply - model.lowply - 1:
            self.plot.select(ply - model.lowply)
        self.plot.redraw()

        # Uncomment this to debug eval function
        return

        board = model.boards[-1].board
        opboard = model.boards[-1].clone().board
        opboard.setColor(1 - opboard.color)
        material, phase = leval.evalMaterial(board)
        if board.color == WHITE:
            print("material", -material)
            e1 = leval.evalKingTropism(board)
            e2 = leval.evalKingTropism(opboard)
            print("evaluation: %d + %d = %d " % (e1, e2, e1 + e2))
            p1 = leval.evalPawnStructure(board, phase)
            p2 = leval.evalPawnStructure(opboard, phase)
            print("pawns: %d + %d = %d " % (p1, p2, p1 + p2))
            print("knights:", -leval.evalKnights(board))
            print("king:", -leval.evalKing(board, phase))
        else:
            print("material", material)
            print("evaluation:", leval.evalKingTropism(board))
            print("pawns:", leval.evalPawnStructure(board, phase))
            print("pawns2:", leval.evalPawnStructure(opboard, phase))
            print("pawns3:", leval.evalPawnStructure(board, phase) +
                  leval.evalPawnStructure(opboard, phase))
            print("knights:", leval.evalKnights(board))
            print("king:", leval.evalKing(board, phase))
        print("----------------------")

    def game_started(self, model):
        self.game_changed(model, model.ply)

    def shownChanged(self, boardview, shown):
        if not boardview.shownIsMainLine():
            return
        if self.plot.selected != shown:
            self.plot.select(shown - self.boardview.model.lowply)
            self.plot.redraw()
            adj = self.sw.get_vadjustment()

            y = self.plot.moveHeight * (shown - self.boardview.model.lowply)
            if y < adj.get_value() or y > adj.get_value() + adj.get_page_size(
            ):
                adj.set_value(min(y, adj.get_upper() - adj.get_page_size()))

    def analysis_changed(self, gamemodel, ply):
        if self.boardview.animating:
            return

        if not self.boardview.shownIsMainLine():
            return
        if ply - gamemodel.lowply > len(self.plot.scores) - 1:
            # analysis line of yet undone position
            return

        color = (ply - 1) % 2
        score = gamemodel.scores[ply][1]
        score = score * -1 if color == WHITE else score
        self.plot.changeScore(ply - gamemodel.lowply, score)
        self.plot.select(ply)
        self.plot.redraw()

    def plot_selected(self, plot, selected):
        try:
            board = self.boardview.model.boards[selected]
        except IndexError:
            return
        self.boardview.setShownBoard(board)


class ScorePlot(Gtk.DrawingArea):

    __gtype_name__ = "ScorePlot" + str(randint(0, sys.maxsize))

    __gsignals__ = {"selected": (GObject.SignalFlags.RUN_FIRST, None, (int, ))}

    def __init__(self, boardview):
        GObject.GObject.__init__(self)
        self.boardview = boardview
        self.connect("draw", self.expose)
        self.connect("button-press-event", self.press)
        self.props.can_focus = True
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.KEY_PRESS_MASK)
        self.moveHeight = 12
        self.scores = []
        self.selected = 0

    def addScore(self, score):
        self.scores.append(score)

    def changeScore(self, ply, score):
        if self.scores:
            self.scores[ply] = score

    def __len__(self):
        return len(self.scores)

    def undo(self):
        del self.scores[-1]

    def select(self, index):
        self.selected = index

    def clear(self):
        del self.scores[:]

    @idle_add
    def redraw(self):
        if self.get_window():
            a = self.get_allocation()
            rect = Gdk.Rectangle()
            rect.x, rect.y, rect.width, rect.height = (0, 0, a.width, a.height)
            self.get_window().invalidate_rect(rect, True)
            self.get_window().process_updates(True)

    def press(self, widget, event):
        self.grab_focus()
        self.emit('selected', event.y / self.moveHeight)

    def expose(self, widget, context):
        a = widget.get_allocation()
        context.rectangle(a.x, a.y, a.width, a.height)
        context.clip()
        self.draw(context)
        self.set_size_request(-1, (len(self.scores)) * self.moveHeight)
        return False

    def draw(self, cr):
        m = self.boardview.model
        if m.isPlayingICSGame():
            return

        width = self.get_allocation().width
        height = len(self.scores) * self.moveHeight

        ########################################
        # Draw background                      #
        ########################################

        cr.set_source_rgb(1, 1, 1)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        ########################################
        # Draw dark middle line                #
        ########################################

        cr.set_source_rgb(1, 0, 0)
        cr.move_to(width / 2., 0)
        cr.line_to(width / 2., height)
        cr.set_line_width(0.25)
        cr.stroke()

        ########################################
        # Draw the actual plot (dark area)     #
        ########################################

        # sign = lambda n: n == 0 and 1 or n / abs(n)
        def sign(n):
            return n == 0 and 1 or n / abs(n)

        def mapper(score):
            return (e**(-5e-4 * abs(score)) - 1) * sign(score)

        if self.scores:
            # mapper = lambda score: (e**(-5e-4 * abs(score)) - 1) * sign(score)
            cr.set_source_rgb(0, 0, 0)
            cr.move_to(width, 0)
            cr.line_to(width / 2 - width / 2 * mapper(self.scores[0]), 0)
            for i, score in enumerate(self.scores):
                x = width / 2 - width / 2 * mapper(score)
                y = (i + 1) * self.moveHeight
                cr.line_to(x, y)
            cr.line_to(width, height)
            cr.fill_preserve()

        ########################################
        # Draw light middle line               #
        ########################################

        cr.save()
        cr.clip()
        cr.set_source_rgb(1, 1, 1)
        cr.move_to(width / 2., 0)
        cr.line_to(width / 2., height)
        cr.set_line_width(0.15)
        cr.stroke()
        cr.restore()

        ########################################
        # Draw selection                       #
        ########################################

        lw = 2.
        cr.set_line_width(lw)
        y = (self.selected) * self.moveHeight
        cr.rectangle(lw / 2, y - lw / 2, width - lw, self.moveHeight + lw)
        sc = self.get_style_context()
        found, color = sc.lookup_color("p_bg_selected")
        cr.set_source_rgba(color.red, color.green, color.blue, .15)
        cr.fill_preserve()
        cr.set_source_rgb(color.red, color.green, color.blue)
        cr.stroke()

import sys
from math import e, floor
from random import randint

from gi.repository import Gtk, GObject
from gi.repository import Gdk

from pychess.System import uistuff, conf
from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import WHITE, DRAW, WHITEWON, BLACKWON
from pychess.Utils.lutils import leval

__title__ = _("Score")
__icon__ = addDataPrefix("glade/panel_score.svg")
__desc__ = _("The score panel tries to evaluate the positions and shows you a graph of the game progress")


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

        def cb_config_changed(none):
            self.fetch_chess_conf()
            self.plot.redraw()
        self.cids_conf = [
            conf.notify_add("scoreLinearScale", cb_config_changed)
        ]
        self.fetch_chess_conf()

        uistuff.keepDown(__widget__)

        return __widget__

    def fetch_chess_conf(self):
        self.plot.linear_scale = conf.get("scoreLinearScale")

    def on_game_terminated(self, model):
        self.plot.disconnect(self.plot_cid)
        self.boardview.disconnect(self.cid)
        for cid in self.model_cids:
            self.boardview.model.disconnect(cid)
        for cid in self.cids_conf:
            conf.notify_remove(cid)

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
                points = points * -1 if i % 2 == 1 else points
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
                points = points * -1 if ply % 2 == 1 else points
            else:
                try:
                    points = leval.evaluateComplete(
                        model.getBoardAtPly(ply).board, WHITE)
                except IndexError:
                    return
        self.plot.addScore(points)

        # As shownChanged will normally be emitted just after game_changed -
        # if we are viewing the latest position - we can do the selection change
        # now, and thereby avoid redraw being called twice
        if self.plot.selected == ply - model.lowply - 1:
            self.plot.select(ply - model.lowply)
        self.plot.redraw()

        # Uncomment this to debug eval function
        # ---
        # board = model.boards[-1].board
        # opboard = model.boards[-1].clone().board
        # opboard.setColor(1 - opboard.color)
        # material, phase = leval.evalMaterial(board)
        # if board.color == WHITE:
        #     print("material", -material)
        #     e1 = leval.evalKingTropism(board)
        #     e2 = leval.evalKingTropism(opboard)
        #     print("evaluation: %d + %d = %d " % (e1, e2, e1 + e2))
        #     p1 = leval.evalPawnStructure(board, phase)
        #     p2 = leval.evalPawnStructure(opboard, phase)
        #     print("pawns: %d + %d = %d " % (p1, p2, p1 + p2))
        #     print("knights:", -leval.evalKnights(board))
        #     print("king:", -leval.evalKing(board, phase))
        # else:
        #     print("material", material)
        #     print("evaluation:", leval.evalKingTropism(board))
        #     print("pawns:", leval.evalPawnStructure(board, phase))
        #     print("pawns2:", leval.evalPawnStructure(opboard, phase))
        #     print("pawns3:", leval.evalPawnStructure(board, phase) +
        #           leval.evalPawnStructure(opboard, phase))
        #     print("knights:", leval.evalKnights(board))
        #     print("king:", leval.evalKing(board, phase))
        # print("----------------------")

    def game_started(self, model):
        if model.lesson_game:
            return

        self.game_changed(model, model.ply)

    def shownChanged(self, boardview, shown):
        if not boardview.shownIsMainLine():
            return
        if self.plot.selected != shown:
            self.plot.select(shown - self.boardview.model.lowply)
            self.plot.redraw()

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
        self.scores = []
        self.selected = 0

    def get_move_height(self):
        c = self.__len__()
        w = self.get_allocation().width
        if c != 0:
            w = int(floor(w / c))
        return max(min(w, 24), 1)

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

    def redraw(self):
        if self.get_window():
            a = self.get_allocation()
            rect = Gdk.Rectangle()
            rect.x, rect.y, rect.width, rect.height = (0, 0, a.width, a.height)
            self.get_window().invalidate_rect(rect, True)
            self.get_window().process_updates(True)

    def press(self, widget, event):
        self.grab_focus()
        self.emit('selected', event.x / self.get_move_height())

    def expose(self, widget, context):
        a = widget.get_allocation()
        context.rectangle(0, 0, a.width, a.height)
        context.clip()
        self.draw(context)
        return False

    def draw(self, cr):
        m = self.boardview.model
        if m.isPlayingICSGame():
            return

        width = self.get_allocation().width
        height = self.get_allocation().height

        ########################################
        # Draw background                      #
        ########################################

        cr.set_source_rgb(1, 1, 1)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        ########################################
        # Draw the actual plot (dark area)     #
        ########################################

        def sign(n):
            return n == 0 and 1 or n / abs(n)

        def mapper(score):
            if self.linear_scale:
                return min(abs(score), 800) / 800 * sign(score)  # Linear
            else:
                return (e ** (5e-4 * abs(score)) - 1) * sign(score)  # Exponentially stretched

        if self.scores:
            cr.set_source_rgb(0, 0, 0)
            cr.move_to(0, height)
            cr.line_to(0, (height / 2.) * (1 + mapper(self.scores[0])))
            for i, score in enumerate(self.scores):
                x = (i + 1) * self.get_move_height()
                y = (height / 2.) * (1 + mapper(score))
                y = max(0, min(height, y))
                cr.line_to(x, y)
            cr.line_to(x, height)
            cr.fill()
        else:
            x = 0
        cr.set_source_rgb(0.9, 0.9, 0.9)
        cr.rectangle(x, 0, width, height)
        cr.fill()

        ########################################
        # Draw middle line and markers         #
        ########################################

        cr.set_line_width(0.25)
        markers = [16, -16, 8, -8, 3, -3, 0]  # centipawns
        for mark in markers:
            if mark == 0:
                cr.set_source_rgb(1, 0, 0)
            else:
                cr.set_source_rgb(0.85, 0.85, 0.85)
            y = (height / 2.) * (1 + mapper(100 * mark))
            y = max(0, min(height, y))
            cr.move_to(0, y)
            cr.line_to(width, y)
            cr.stroke()

        ########################################
        # Draw selection                       #
        ########################################

        lw = 2
        cr.set_line_width(lw)
        s = self.get_move_height()
        x = self.selected * s
        cr.rectangle(x - lw / 2, lw / 2, s + lw, height - lw)
        found, color = self.get_style_context().lookup_color("p_bg_selected")
        cr.set_source_rgba(color.red, color.green, color.blue, .15)
        cr.fill_preserve()
        cr.set_source_rgb(color.red, color.green, color.blue)
        cr.stroke()

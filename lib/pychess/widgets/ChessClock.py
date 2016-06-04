# -*- coding: UTF-8 -*-

from __future__ import absolute_import

from math import ceil, pi, cos, sin

import cairo
from gi.repository import GLib, Gtk, Gdk, Pango, PangoCairo, GObject

from pychess.System import conf
from pychess.Utils.const import BLACK, WHITE, LOCAL, UNFINISHED_STATES
from . import preferencesDialog


def formatTime(seconds, clk2pgn=False):
    minus = ""
    if seconds not in range(-10, 10):
        seconds = ceil(seconds)
    if seconds < 0:
        minus = "-"
        seconds = -seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours or clk2pgn:
        return minus + "%d:%02d:%02d" % (hours, minutes, seconds)
    elif not minutes and seconds < 10:
        return minus + "%.1f" % seconds
    else:
        return minus + "%d:%02d" % (minutes, seconds)


class ChessClock(Gtk.DrawingArea):
    def __init__(self):
        GObject.GObject.__init__(self)
        self.connect("draw", self.expose)
        self.names = [_("White"), _("Black")]

        self.model = None
        self.short_on_time = [False, False]

    def expose(self, widget, ctx):
        context = widget.get_window().cairo_create()
        clip_ext = context.clip_extents()
        rec = Gdk.Rectangle()
        rec.x, rec.y, rec.width, rec.height = clip_ext[0], clip_ext[1], \
            clip_ext[2] - clip_ext[0], clip_ext[3] - clip_ext[1]
        context.rectangle(rec.x, rec.y, rec.width, rec.height)
        context.clip()
        self.draw(context)
        return False

    def draw(self, context):

        style_ctxt = self.get_style_context()
        self.light = style_ctxt.lookup_color("p_light_color")[1]
        self.dark = style_ctxt.lookup_color("p_dark_color")[1]
        if not self.model:
            return

        # Draw graphical Clock. Should this be moved to preferences?
        drawClock = True

        rect = Gdk.Rectangle()
        clip_ext = context.clip_extents()
        rect.x, rect.y, rect.width, rect.height = clip_ext[0], clip_ext[1], \
            clip_ext[2] - clip_ext[0], clip_ext[3] - clip_ext[1]
        context.rectangle(rect.width / 2. * self.model.movingColor, 0,
                          rect.width / 2., rect.height)

        context.set_source_rgba(self.dark.red, self.dark.green, self.dark.blue,
                                self.dark.alpha)
        context.fill_preserve()
        context.new_path()

        time0 = self.names[0], self.formatedCache[WHITE]
        layout0 = self.create_pango_layout(" %s: %s " % (time0))
        layout0.set_font_description(Pango.FontDescription("Sans Serif 17"))

        time1 = self.names[1], self.formatedCache[BLACK]
        layout1 = self.create_pango_layout(" %s: %s " % (time1))
        layout1.set_font_description(Pango.FontDescription("Sans Serif 17"))

        dbl_max = max(layout1.get_pixel_size()[0], layout0.get_pixel_size()[0]) * 2
        self.set_size_request(dbl_max + rect.height + 7, -1)

        pangoScale = float(Pango.SCALE)

        # Analog clock code.
        def paintClock(player):
            clock_y = rect.height / 2.
            clock_x = clock_y + rect.width / 2. * player + 1
            rec = rect.height / 2. - 3.5

            context.arc(clock_x, clock_y, rec - 1, 0, 2 * pi)
            linear = cairo.LinearGradient(clock_x - rec * 2, clock_y - rec * 2,
                                          clock_x + rec * 2, clock_y + rec * 2)
            linear.add_color_stop_rgba(0, 1, 1, 1, 0.3)
            linear.add_color_stop_rgba(1, 0, 0, 0, 0.3)
            # context.set_source_rgba( 0, 0, 0, .3)
            context.set_source(linear)
            context.fill()

            linear = cairo.LinearGradient(clock_x - rec, clock_y - rec,
                                          clock_x + rec, clock_y + rec)
            linear.add_color_stop_rgba(0, 0, 0, 0, 0.5)
            linear.add_color_stop_rgba(1, 1, 1, 1, 0.5)
            context.arc(clock_x, clock_y, rec, 0, 2 * pi)
            context.set_source(linear)
            context.set_line_width(2.5)
            context.stroke()

            starttime = float(self.model.getInitialTime()) or 1
            used = self.model.getPlayerTime(player) / starttime
            if used > 0:
                if used > 0:
                    context.arc(clock_x, clock_y, rec - .8, -(used + 0.25) * 2 * pi, -0.5 *
                                pi)
                    context.line_to(clock_x, clock_y)
                    context.close_path()
                elif used == 0:
                    context.arc(clock_x, clock_y, rec - .8, -0.5 * pi, 1.5 * pi)
                    context.line_to(clock_x, clock_y)

                radial = cairo.RadialGradient(clock_x, clock_y, 3, clock_x, clock_y, rec)
                if player == 0:
                    # radial.add_color_stop_rgb(0, .73, .74, .71)
                    radial.add_color_stop_rgb(0, .93, .93, .92)
                    radial.add_color_stop_rgb(1, 1, 1, 1)
                else:
                    # radial.add_color_stop_rgb(0, .53, .54, .52)
                    radial.add_color_stop_rgb(0, .18, .20, .21)
                    radial.add_color_stop_rgb(1, 0, 0, 0)
                context.set_source(radial)
                context.fill()

                x_loc = clock_x - cos((used - 0.25) * 2 * pi) * (rec - 1)
                y_loc = clock_y + sin((used - 0.25) * 2 * pi) * (rec - 1)
                context.move_to(clock_x, clock_y - rec + 1)
                context.line_to(clock_x, clock_y)
                context.line_to(x_loc, y_loc)
                context.set_line_width(0.2)
                if player == 0:
                    context.set_source_rgb(0, 0, 0)
                else:
                    context.set_source_rgb(1, 1, 1)
                context.stroke()

        if drawClock:
            paintClock(WHITE)
        if (self.model.movingColor or WHITE) == WHITE:
            context.set_source_rgba(self.light.red, self.light.green,
                                    self.light.blue, self.light.alpha)
        else:
            context.set_source_rgba(self.dark.red, self.dark.green,
                                    self.dark.blue, self.dark.alpha)
        y_loc = rect.height / 2. - layout0.get_extents()[0].height / pangoScale / 2 \
            - layout0.get_extents()[0].y / pangoScale
        context.move_to(rect.height - 7, y_loc)
        PangoCairo.show_layout(context, layout0)

        if drawClock:
            paintClock(BLACK)
        if self.model.movingColor == BLACK:
            context.set_source_rgba(self.light.red, self.light.green,
                                    self.light.blue, self.light.alpha)
        else:
            context.set_source_rgba(self.dark.red, self.dark.green,
                                    self.dark.blue, self.dark.alpha)
        y_loc = rect.height / 2. - layout0.get_extents()[0].height / pangoScale / 2 \
            - layout0.get_extents()[0].y / pangoScale
        context.move_to(rect.width / 2. + rect.height - 7, y_loc)
        PangoCairo.show_layout(context, layout1)

    def redraw_canvas(self):
        def do_redraw_canvas():
            if self.get_window():
                allocation = self.get_allocation()
                rect = Gdk.Rectangle()
                rect.x, rect.y, rect.width, rect.height = (0, 0, allocation.width,
                                                           allocation.height)
                self.get_window().invalidate_rect(rect, True)
                self.get_window().process_updates(True)

        GLib.idle_add(do_redraw_canvas)

    def setModel(self, model):
        self.model = model
        self.model.connect("time_changed", self.time_changed)
        self.model.connect("player_changed", self.player_changed)
        self.formatedCache = [formatTime(self.model.getPlayerTime(
            self.model.movingColor or WHITE))] * 2
        if model.secs != 0 or model.gain != 0:
            GObject.timeout_add(100, self.update)

    def time_changed(self, model):
        self.update()

    def player_changed(self, model):
        self.redraw_canvas()

    def update(self, wmovecount=-1, bmovecount=-1):
        if self.model.ended:
            return False
        alarm_time = int(conf.get("alarm_spin", 15))
        if self.model.getPlayerTime(self.model.movingColor) <= alarm_time and \
            self.model.gamemodel.players[self.model.movingColor].__type__ == LOCAL and \
            self.model.gamemodel.status in UNFINISHED_STATES and \
                not self.short_on_time[self.model.movingColor]:
            self.short_on_time[self.model.movingColor] = True
            preferencesDialog.SoundTab.playAction("shortOnTime")

        if self.model.paused and wmovecount == -1 and bmovecount == -1:
            return not self.model.ended
        white_time = formatTime(self.model.getPlayerTime(WHITE, wmovecount))
        black_time = formatTime(self.model.getPlayerTime(BLACK, bmovecount))
        if self.formatedCache != [white_time, black_time]:
            self.formatedCache = [white_time, black_time]
            self.redraw_canvas()
        return not self.model.ended

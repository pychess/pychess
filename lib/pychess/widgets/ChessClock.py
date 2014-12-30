# -*- coding: UTF-8 -*-

from __future__ import absolute_import

from math import ceil, pi, cos, sin
import cairo
from gi.repository import Gtk, Pango
from gi.repository import Gdk
from gi.repository import PangoCairo
from gi.repository import GObject

from pychess.System import conf
from pychess.System import glock
from pychess.System.repeat import repeat_sleep
from pychess.Utils.const import WHITE, BLACK
from . import preferencesDialog


def formatTime(seconds, clk2pgn=False):
    if not -10 <= seconds <= 10:
        seconds = ceil(seconds)
    minus = "-" if seconds < 0 else ""
    if minus:
        seconds = -seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours or clk2pgn:
        return minus+"%d:%02d:%02d" % (hours, minutes, seconds)
    elif not minutes and seconds < 10:
        return minus+"%.1f" % seconds
    else:
        return minus+"%d:%02d" % (minutes, seconds)

class ChessClock (Gtk.DrawingArea):
    
    def __init__(self):        
        GObject.GObject.__init__(self)
        self.connect("draw", self.expose)
        self.names = [_("White"),_("Black")]
        
        self.model = None
        self.short_on_time = [False, False]
        
    def expose(self, widget, ctx):        
        context = widget.get_window().cairo_create()
        a = widget.get_allocation()
        context.rectangle(a.x, a.y,
                          a.width, a.height)       
        context.clip()
        self.draw(context)
        return False
    
    def draw(self, context):
       
        sc = self.get_style_context()
        bool1, self.light = sc.lookup_color("p_light_color")    
        bool1, self.dark = sc.lookup_color("p_dark_color")        
        if not self.model: return
        
        # Draw graphical Clock. Should this be moved to preferences?
        drawClock = True 
        
        rect = self.get_allocation()
        context.rectangle(
            rect.width/2. * self.model.movingColor, 0,
            rect.width/2., rect.height)
        
        context.set_source_rgba(self.dark.red, self.dark.green, self.dark.blue, self.dark.alpha)       
        context.fill_preserve()
        context.new_path()
        
        time0 = self.names[0], self.formatedCache[WHITE]
        layout0 = self.create_pango_layout(" %s: %s " % (time0))
        layout0.set_font_description(Pango.FontDescription("Sans Serif 17"))
        
        time1 = self.names[1], self.formatedCache[BLACK]
        layout1 = self.create_pango_layout(" %s: %s " % (time1))
        layout1.set_font_description(Pango.FontDescription("Sans Serif 17"))
        
        w = max(layout1.get_pixel_size()[0], layout0.get_pixel_size()[0])*2
        self.set_size_request(w+rect.height+7, -1)
        
        pangoScale = float(Pango.SCALE)
        
        # Analog clock code.
        def paintClock (player):
            cy = rect.height/2.
            cx = cy + rect.width/2.*player + 1
            r = rect.height/2.-3.5
            
            context.arc(cx,cy, r-1, 0, 2*pi)
            linear = cairo.LinearGradient(cx-r*2, cy-r*2, cx+r*2, cy+r*2)
            linear.add_color_stop_rgba(0, 1, 1, 1, 0.3)
            linear.add_color_stop_rgba(1, 0, 0, 0, 0.3)
            #context.set_source_rgba( 0, 0, 0, .3)
            context.set_source(linear)
            context.fill()
            
            linear = cairo.LinearGradient(cx-r, cy-r, cx+r, cy+r)
            linear.add_color_stop_rgba(0, 0, 0, 0, 0.5)
            linear.add_color_stop_rgba(1, 1, 1, 1, 0.5)
            context.arc(cx,cy, r, 0, 2*pi)
            context.set_source(linear)
            context.set_line_width(2.5)
            context.stroke()
            
            starttime = float(self.model.getInitialTime()) or 1
            used = self.model.getPlayerTime(player) / starttime
            if used > 0:
                if used > 0:
                    context.arc(cx,cy, r-.8, -(used+0.25)*2*pi, -0.5*pi)
                    context.line_to(cx,cy)
                    context.close_path()
                elif used == 0:
                    context.arc(cx,cy, r-.8, -0.5*pi, 1.5*pi)
                    context.line_to(cx,cy)
                
                radial = cairo.RadialGradient(cx,cy, 3, cx,cy,r)
                if player == 0:
                    #radial.add_color_stop_rgb(0, .73, .74, .71)
                    radial.add_color_stop_rgb(0, .93, .93, .92)
                    radial.add_color_stop_rgb(1, 1, 1, 1)
                else:
                    #radial.add_color_stop_rgb(0, .53, .54, .52)
                    radial.add_color_stop_rgb(0, .18, .20, .21)
                    radial.add_color_stop_rgb(1, 0, 0, 0)
                context.set_source(radial)
                context.fill()
                
                x = cx - cos((used-0.25)*2*pi)*(r-1)
                y = cy + sin((used-0.25)*2*pi)*(r-1)
                context.move_to(cx,cy-r+1)
                context.line_to(cx,cy)
                context.line_to(x,y)
                context.set_line_width(0.2)
                if player == 0:
                    context.set_source_rgb(0,0,0)
                else: context.set_source_rgb(1,1,1)
                context.stroke()
        
        if drawClock:
            paintClock (WHITE)
        if (self.model.movingColor or WHITE) == WHITE:          
            context.set_source_rgba(self.light.red, self.light.green, self.light.blue, self.light.alpha) 
        else:          
            context.set_source_rgba(self.dark.red, self.dark.green, self.dark.blue, self.dark.alpha)        
        y = rect.height/2. - layout0.get_extents()[0].height/pangoScale/2 \
                           - layout0.get_extents()[0].y/pangoScale
        context.move_to(rect.height-7,y)       
        PangoCairo.show_layout(context, layout0)

        if drawClock:
            paintClock (BLACK)
        if self.model.movingColor == BLACK:            
            context.set_source_rgba(self.light.red, self.light.green, self.light.blue, self.light.alpha)
        else:
            context.set_source_rgba(self.dark.red, self.dark.green, self.dark.blue, self.dark.alpha)       
        y = rect.height/2. - layout0.get_extents()[0].height/pangoScale/2 \
                           - layout0.get_extents()[0].y/pangoScale
        context.move_to(rect.width/2. + rect.height-7, y)        
        PangoCairo.show_layout(context, layout1)

    def redraw_canvas(self):
        if self.get_window():
            glock.acquire()
            try:
                if self.get_window():
                    a = self.get_allocation()
                    rect = Gdk.Rectangle()
                    rect.x, rect.y, rect.width, rect.height = (0, 0, a.width, a.height)
                    self.get_window().invalidate_rect(rect, True)
                    self.get_window().process_updates(True)
            finally:
                glock.release()
    
    def setModel (self, model):
        self.model = model
        self.model.connect("time_changed", self.time_changed)
        self.model.connect("player_changed", self.player_changed)
        self.formatedCache = [formatTime (
            self.model.getPlayerTime (self.model.movingColor or WHITE))] * 2
        if model.secs!=0 or model.gain!=0:
            repeat_sleep(self.update, 0.1)
    
    def time_changed (self, model):
        self.update()
    
    def player_changed (self, model):
        self.redraw_canvas()
    
    def update(self, wmovecount=-1, bmovecount=-1):
        alarm_time = int(conf.get("alarm_spin", 15))
        if self.model.getPlayerTime(self.model.movingColor) <= alarm_time and \
            not self.short_on_time[self.model.movingColor]:
            self.short_on_time[self.model.movingColor] = True
            preferencesDialog.SoundTab.playAction("shortOnTime")

        if self.model.paused and wmovecount == -1 and bmovecount == -1:
            return not self.model.ended
        wt = formatTime (self.model.getPlayerTime(WHITE, wmovecount))
        bt = formatTime (self.model.getPlayerTime(BLACK, bmovecount))
        if self.formatedCache != [wt, bt]:
            self.formatedCache = [wt, bt]
            self.redraw_canvas()
        return not self.model.ended

import pygtk
pygtk.require("2.0")
from gtk import gdk
import gtk, time, gobject, pango
from math import ceil, floor, pi, cos, sin
from threading import Thread
import cairo

class ChessClock (gtk.DrawingArea):
    __gsignals__ = {'time_out' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_INT,))}

    def __init__(self):
        super(ChessClock, self).__init__()
        self.connect("expose_event", self.expose)
        self.names = [_("White"),_("Black")]
        self.setTime(0)
    
    def expose(self, widget, event):
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
        context.clip()
        self.draw(context)
        return False

    def draw(self, context):
        self.dark = self.get_style().dark[gtk.STATE_NORMAL]
        self.light = self.get_style().light[gtk.STATE_NORMAL]
        
        #FIXME: The clock will always redraw everything,
        #while the next line is outcommented
        #Problem is that saving the redrawingAll in self,
        #will make natural redraws, as when hidden under another window,
        #only drafw the one side, and leave the other empty.
        #ra = self.redrawingAll
        ra = True
        
        if ra or self.player == 0:
            time0 = self.names[0],self.formatTime(self.getDeciSeconds(0))
            layout0 = self.create_pango_layout(" %s: %s " % (time0))
            layout0.set_font_description(pango.FontDescription("Sans Serif 17"))
        
        if ra or self.player == 1:
            time1 = self.names[1],self.formatTime(self.getDeciSeconds(1))
            layout1 = self.create_pango_layout(" %s: %s " % (time1))
            layout1.set_font_description(pango.FontDescription("Sans Serif 17"))
        
        if ra:
            w = max(layout1.get_pixel_size()[0], layout0.get_pixel_size()[0])*2
            self.set_size_request(w, self.get_size_request()[1])
        
        rect = self.get_allocation()
        context.rectangle(
            rect.width/2. * self.player, 0,
            rect.width/2., rect.height)
        context.set_source_color(self.dark)
        context.fill_preserve()
        context.new_path()
        
        # Analog clock code. Testing
        
        c = rect.height/2.
        r = rect.height/2.-5
        
        context.arc(c,c, r-1, 0, 2*pi)
        context.set_source_rgba( .5, .5, .5, .3)
        context.fill()
        
        linear = cairo.LinearGradient(c-r, c-r, c+r, c+r)
        linear.add_color_stop_rgba(0, 0, 0, 0, 0.5)
        linear.add_color_stop_rgba(1, 1, 1, 1, 0.5)
        context.arc(c,c, r, 0, 2*pi)
        context.set_source(linear)
        context.stroke()
        
        time = self.time != 0 and self.time or 1
        used = self.getDeciSeconds(0) / float(time)
        if used > 0:
            if used > 0:
                context.arc(c,c, r-1.5, -(used+0.25)*2*pi, -0.5*pi)
                context.line_to(c,c)
                context.close_path()
            elif used == 0:
                context.arc(c,c, r-2, -0.5*pi, 1.5*pi)
                context.line_to(c,c)
            
            radial = cairo.RadialGradient(c,c, 3, c,c,r)
            radial.add_color_stop_rgb(0, .73, .74, .71)
            radial.add_color_stop_rgb(1, .93, .93, .92)
            context.set_source(radial)
            context.fill()
        
            x = c - cos((used-0.25)*2*pi)*(r-1)
            y = c + sin((used-0.25)*2*pi)*(r-1)
            context.move_to(c,c-r)
            context.line_to(c,c)
            context.line_to(x,y)
            context.set_line_width(0.4)
            context.set_source_rgb(0,0,0)
            context.stroke()
        
        pangoScale = float(pango.SCALE)
        
        if ra or self.player == 0:
            if self.player == 0:
                context.set_source_color(self.light)
            y = rect.height/2. - layout0.get_extents()[0][3]/pangoScale/2 \
                               - layout0.get_extents()[0][1]/pangoScale
            context.move_to(r*2,y)
            context.show_layout(layout0)
        
        if ra or self.player == 1:
            if self.player == 1:
                context.set_source_color(self.light)
            else: context.set_source_color(self.dark)
            y = rect.height/2. - layout1.get_extents()[0][3]/pangoScale/2 \
                               - layout1.get_extents()[0][1]/pangoScale
            context.move_to(rect.width/2.,y)
            context.show_layout(layout1)

    redrawingAll = True
    def redraw_canvas(self, all=True):
        self.redrawingAll = all
        if self.window:
            def func():
                a = self.get_allocation()
                if not all and self.player == 0:
                    rect = gdk.Rectangle(0, 0, a.width/2, a.height)
                elif not all and self.player == 1:
                    rect = gdk.Rectangle(a.width/2, 0, a.width/2, a.height)
                else: rect = gdk.Rectangle(0, 0, a.width, a.height)
                self.window.invalidate_rect(rect, True)
                self.window.process_updates(True)
            gobject.idle_add(func)

    emited = False
    def update(self):
        self.ptemp[self.player] -= 1
        self.redraw_canvas(False)
        
        if self.ptemp[self.player] <= 0 and not self.emited:
            self.emit_time_out_signal(self.player)
            self.emited = True

        return True
    
    def reset (self):
        self.emited = False
        self.time = 0
        self.gain = 0
        self.thread = None
        self.p = [None, None]
        self.ptemp = [None, None]
        self.startTime = None
        self._player = 0
    
    def emit_time_out_signal(self, player):
        self.emit("time_out", player)

    def formatTime(self, dseconds):
        seconds = dseconds / 10
        if not -10 <= seconds <= 10: seconds = ceil(seconds)
        minus = seconds < 0 and "-" or ""
        if minus: seconds = -seconds
        h = int(seconds / 3600)
        m = int(seconds % 3600 / 60)
        s = seconds % 60
        if h: return minus+"%d:%02d:%02d" % (h,m,s)
        elif not m and s < 10: return minus+"%.1f" % s
        else: return minus+"%d:%02d" % (m,s)

    time = 0
    def setTime(self, time):
        self.p = [time,time]
        self.ptemp = [time,time]
        self.time = time
        self.redraw_canvas()
    
    gain = 0
    def setGain(self, gain):
        self.gain = gain
    
    def start(self):
        self.thread = gobject.timeout_add(100, self.update)
    
    thread = None
    def stop(self):
        self.redraw_canvas()
        if self.thread:
            gobject.source_remove(self.thread)
    
    def switch(self):
        self.player = 1 - self.player
    
    p = [None, None]
    ptemp = [None, None]
    def getDeciSeconds (self, player):
        if not self.p[player]: return 0
        if self.player == player:
            return self.ptemp[player]
        return self.p[player]
    
    startTime = None
    _player = 0
    def _get_player(self):
        return self._player
        
    def _set_player(self, player):
        if player == self._player: return
        
        if self.startTime != None:
            dsecs = (time.time() - self.startTime)*10
            self.p[self.player] = self.p[self.player] - dsecs + self.gain
        else:
            self.p[self.player] += self.gain
        self.ptemp[self.player] = self.p[self.player]
        
        self._player = player
       
        self.stop()
        self.startTime = time.time()
        self.start()
        
    player = property(_get_player, _set_player)

    def _get_playerTime (self, player):
        return self.ptemp[player]
    p0time = property(lambda: self._get_playerTime(0))
    p1time = property(lambda: self._get_playerTime(1))

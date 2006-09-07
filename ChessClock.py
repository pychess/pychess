import pygtk
pygtk.require("2.0")
from gtk import gdk
import gtk, time, gobject, pango
from math import ceil, floor
from threading import Thread

class ChessClock (gtk.DrawingArea):
    __gsignals__ = {'time_out' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_INT,))}

    def __init__(self):
        super(ChessClock, self).__init__()
        self.connect("expose_event", self.expose)
        self.names = ["White","Black"]
        self.setTime(0)
    
    def reset (self):
        pass #TODO
    
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
        
        hpad, vpad = 7, 1
        ra = self.redrawingAll
        
        if ra or self.player == 0:
            time0 = self.names[0],self.formatTime(self.getDeciSeconds(0))     
            layout0 = self.create_pango_layout("%s: %s" % (time0))
            layout0.set_font_description(pango.FontDescription("Sans Serif 17"))
        
        if ra or self.player == 1:
            time1 = self.names[1],self.formatTime(self.getDeciSeconds(1))
            layout1 = self.create_pango_layout("%s: %s" % (time1))
            layout1.set_font_description(pango.FontDescription("Sans Serif 17"))
        
        if ra:
            w = layout1.get_pixel_size()[0] + layout0.get_pixel_size()[0]
            self.set_size_request(w+hpad*4, self.get_size_request()[1])
        
        rect = self.get_allocation()
        context.rectangle(
            float(rect.width)/2 * self.player, 0,
            float(rect.width)/2, rect.height)
        context.set_source_color(self.dark)
        context.fill_preserve()
        context.new_path()
        
        if ra or self.player == 0:
            if self.player == 0:
                context.set_source_color(self.light)
            context.move_to(hpad,vpad)
            context.show_layout(layout0)
        
        if ra or self.player == 1:
            if self.player == 1:
                context.set_source_color(self.light)
            else: context.set_source_color(self.dark)
            context.move_to(float(rect.width)/2+hpad,vpad)
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

    def update(self):
        self.ptemp[self.player] -= 1
        self.redraw_canvas(False)
        
        if self.ptemp[self.player] <= 0:
            self.emit_time_out_signal(self.player)

        return True

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
       
        self.redraw_canvas()
        self.stop()
        self.startTime = time.time()
        self.start()
        
    player = property(_get_player, _set_player)

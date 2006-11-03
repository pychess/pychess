#TODO: Add zoom buttons

import gtk, gobject
from math import e
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE, TYPE_INT

class ScorePlot (gtk.DrawingArea):
    
    __gtype_name__ = "ScorePlot"
    
    __gsignals__ = {
        "selected" : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_INT,))
    }
    
    def __init__ (self):
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.expose)
        self.connect("button-press-event", self.press)
        self.set_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.moveHeight = 12
        self.maxScore = 10**3
        self.scores = []
        self.selected = 0
        
    def addScore (self, score):
        self.scores.append(score)
    
    def select (self, index):
        self.selected = index
    
    def clear (self):
        del self.scores[:]
    
    def redraw (self):
        if self.window:
            def func():
                a = self.get_allocation()
                rect = gtk.gdk.Rectangle(0, 0, a.width, a.height)
                self.window.invalidate_rect(rect, True)
                self.window.process_updates(True)
            gobject.idle_add(func)
    
    def press (self, widget, event):
        self.emit('selected', int(event.y/self.moveHeight)+1)
    
    def expose (self, widget, event):
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
        context.clip()
        self.draw(context)
        self.set_size_request(-1, max(0,(len(self.scores)-1)*self.moveHeight))
        return False
    
    def draw (self, cr):
        #for score in self.scores:
        #    if abs(score) > self.maxScore:
        #        self.maxScore = abs(score)
        
        width = self.get_allocation().width
        height = (len(self.scores)-1)*self.moveHeight
        
        cr.set_source_rgb (0, 0, 0)
        cr.rectangle(0,0,width,height)
        cr.fill()
        
        cr.set_source_rgb (1, 1, 1)
        cr.move_to(0, 0)
        for i, score in enumerate(self.scores):
            score2 = 1-e**(-1./1000*abs(score/2.))
            if score < 0: score2 = -score2
            x = width/2 + score2*width/2
            y = i * self.moveHeight
            cr.line_to(x, y)
        cr.line_to(0,height)
        cr.fill()
        
        if self.selected >= 1:
            lw = 2.
            cr.set_line_width(lw)
            y = (self.selected-1)*self.moveHeight
            cr.rectangle(lw/2, y-lw/2, width-lw, self.moveHeight+lw)
            col = self.get_style().base[gtk.STATE_SELECTED]
            r, g, b = map(lambda x: x/65535., (col.red, col.green, col.blue))
            cr.set_source_rgba (r, g, b, .15)
            cr.fill_preserve()
            cr.set_source_rgb (r, g, b)
            cr.stroke()
    
__title__ = _("Score")

plot = ScorePlot()
__widget__ = gtk.ScrolledWindow()
__widget__.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
port = gtk.Viewport()
port.add(plot)
port.set_shadow_type(gtk.SHADOW_NONE)
__widget__.add(port)
__widget__.show_all()

def ready (window):
    global history, boardview
    
    boardview = window["BoardControl"].view
    history = boardview.history
    
    plot.connect("selected", plot_selected)
    boardview.connect('shown_changed', shown_changed)
    history.connect("cleared", history_cleared)
    history.connect("changed", history_changed)
    
def history_cleared (history):
    plot.clear()
    history_changed(history)
    shown_changed(None,0)
    
from Utils.eval import evaluateComplete

def history_changed (history):
    points = evaluateComplete(history[-1])
    plot.addScore(points)
    #adj = __widget__.get_hadjustment()
    #adj.set_value(adj.get_property("upper"))

def shown_changed (boardview, shown):
    plot.select(shown)
    plot.redraw()

def plot_selected (plot, selected):
    boardview.shown = selected

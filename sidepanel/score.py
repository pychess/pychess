import gtk, gobject
class ScorePlot (gtk.DrawingArea):

    def __init__ (self):
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.expose)
        self.moveHeight = 12
        self.maxScore = 10**3
        self.scores = []

    def addScore (self, score):
        self.scores.append(score)
    
    def clear (self):
        del self.scores[:]
    
    def redraw (self):
        if self.window:
            def func():
                a = self.get_allocation()
                rect = gtk.gdk.Rectangle(0, 0, a.width, a.height)
                self.window.invalidate_rect(rect, True)
                self.window.process_updates(True)
            func()
    
    def expose (self, widget, event):
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
        context.clip()
        self.draw(context, float(event.area.width))
        self.set_size_request(-1, (len(self.scores)-1)*self.moveHeight)
        return False
    
    def draw (self, cr, width):
        for score in self.scores:
            if abs(score) > self.maxScore:
                self.maxScore = abs(score) +10
        
        height = (len(self.scores)-1)*self.moveHeight
        
        cr.set_source_rgb (0, 0, 0)
        cr.rectangle(0,0,width,height)
        cr.fill()
        
        cr.set_source_rgb (1, 1, 1)
        cr.move_to(0, 0)
        for i, score in enumerate(self.scores):
            x = width/2 + score*width/2/self.maxScore
            y = i * self.moveHeight
            cr.line_to(x, y)
        cr.line_to(0,height)
        cr.fill()
    
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
    global history
    history = window["BoardControl"].view.history
    
    history.connect("cleared", history_cleared)
    history.connect("changed", history_changed)

def history_cleared (history):
    plot.clear()
    history_changed(history)

from Utils.eval import evaluateComplete

def history_changed (history):
    points = evaluateComplete(history)
    plot.addScore(points)
    plot.redraw()
    #adj = __widget__.get_hadjustment()
    #adj.set_value(adj.get_property("upper"))

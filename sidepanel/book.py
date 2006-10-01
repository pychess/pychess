import gtk, gobject, cairo

__title__ = _("Opening Book")

widgets = gtk.glade.XML("sidepanel/book.glade")
tv = widgets.get_widget("treeview")
sw = widgets.get_widget("scrolledwindow")
sw.unparent()
__widget__ = gtk.Alignment(0,0,1,1)
__widget__.add(sw)

store = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
def ready (window):
    tv.set_model(store)
    tv.append_column(gtk.TreeViewColumn("Move", gtk.CellRendererText(), text=0))
    r = gtk.CellRendererText()
    r.set_property("xalign", 1)
    tv.append_column(gtk.TreeViewColumn("Games", r, text=1))
    tv.append_column(gtk.TreeViewColumn("Win/Draw/Loss", window.BookCellRenderer(), data=2))

    window.oracle.connect("foundbook", foundbook)
    window.oracle.connect("clear", clear)

running = None
def clear (oracle):
    if __widget__.get_child() != sw:
        return
    global s
    s = 0
    def runner():
        global s
        def helper():
            global s, running
            if not running: return
            store.clear()
            store.append (["."*s,"",None])
        gobject.idle_add(helper)
        s += 1
        if s > 3: s = 0
        return running
    global running
    running = True
    gobject.timeout_add(250, runner)

int2 = lambda x: x != "" and int(x) or 0
float2 = lambda x: x != "" and float(x) or 0.0

def sortbook (x, y):
    xgames = sum(map(int2,x[2:5]))
    ygames = sum(map(int2,y[2:5]))
    return ygames - xgames

from threading import Condition
cond = Condition()

def foundbook (oracle, book):
    global running
    running = False
    
    book.sort(sortbook)
    def helper():
        store.clear()
        
        #cond.acquire()
        if not book and __widget__.get_child() == sw:
            __widget__.remove(sw)
            label = gtk.Label(_("In this position,\nthere is no book move."))
            label.set_property("yalign",0.1)
            __widget__.add(label)
            __widget__.show_all()
            #cond.release()
            return
        if book and __widget__.get_child() != sw:
            __widget__.remove(__widget__.get_child())
            __widget__.add(sw)
        #cond.release()
            
        
        i = 0
        for move, p, win, draw, loss in book:
            win,draw,loss = map(float2, (win,draw,loss))
            games = win+draw+loss
            if not games: continue
            win,draw,loss = map(lambda x: x/games, (win,draw,loss))
            store.append ([move, str(int(games)), (win,draw,loss)])
    gobject.idle_add(helper)

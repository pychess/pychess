import gtk, gobject, cairo

__title__ = _("Opening Book")

widgets = gtk.glade.XML("sidepanel/book.glade")
tv = widgets.get_widget("treeview")
__widget__ = widgets.get_widget("scrolledwindow")
__widget__.unparent()

store = gtk.ListStore(str, int, gobject.TYPE_PYOBJECT)
def ready (window):
    tv.set_model(store)
    tv.append_column(gtk.TreeViewColumn("Move", gtk.CellRendererText(), text=0))
    r = gtk.CellRendererText()
    r.set_property("xalign", 1)
    tv.append_column(gtk.TreeViewColumn("Games", r, text=1))
    tv.append_column(gtk.TreeViewColumn("Win/Draw/Loss", window.BookCellRenderer(), data=2))

    window.oracle.connect("foundbook", foundbook)

import gobject
def once (func):
    def helper():
        func()
        return False
    gobject.idle_add(helper)

def sortbook (x, y):
    xgames = sum(map(int,x[2:5]))
    ygames = sum(map(int,y[2:5]))
    return ygames - xgames
    
import array

def foundbook (oracle, book):
    book.sort(sortbook)
    def helper():
        store.clear()
        i = 0
        for move, p, win, draw, loss in book:
            win,draw,loss = map(float, (win,draw,loss))
            games = win+draw+loss
            win,draw,loss = map(lambda x: x/games, (win,draw,loss))
            
            #surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 80, 23)
            #context = gtk.gdk.CairoContext(cairo.Context(surface))
            #paintGraph(context,win,draw,loss,80)
            #pixbuf = surfaceToPixbuf(surface)
            
            store.append ([move, int(games), (win,draw,loss)])
    once(helper)

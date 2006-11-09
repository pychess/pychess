import gtk, gobject, cairo
import gamewidget

__title__ = _("Opening Book")

widgets = gtk.glade.XML("sidepanel/book.glade")
tv = widgets.get_widget("treeview")
sw = widgets.get_widget("scrolledwindow")
sw.unparent()
__widget__ = gtk.Alignment(0,0,1,1)
__widget__.add(sw)

store = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
def ready (window, page_num):
    tv.set_model(store)
    tv.append_column(gtk.TreeViewColumn("Move", gtk.CellRendererText(), text=0))
    r = gtk.CellRendererText()
    r.set_property("xalign", 1)
    tv.append_column(gtk.TreeViewColumn("Games", r, text=1))
    tv.append_column(gtk.TreeViewColumn("Win/Draw/Loss", window.BookCellRenderer(), data=2))
    
    global board, boardcontrol
    boardcontrol = gamewidget.getWidgets(page_num)[0]
    board = boardcontrol.view
    board.connect("shown_changed", shown_changed)
    tv.connect("cursor_changed", selection_changed)
    tv.connect("select_cursor_row", selection_changed)
    tv.connect("row-activated", row_activated)

from Utils.book import getOpenings

def shown_changed (board, shown):
    global openings
    openings = getOpenings(board.history[-1])
    openings.sort(lambda a, b: sum(b[1:])-sum(a[1:]))
    
    board.bluearrow = None
    
    def helper():
        store.clear()
        
        if not openings and __widget__.get_child() == sw:
            __widget__.remove(sw)
            label = gtk.Label(_("In this position,\nthere is no book move."))
            label.set_property("yalign",0.1)
            __widget__.add(label)
            __widget__.show_all()
            return
        if openings and __widget__.get_child() != sw:
            __widget__.remove(__widget__.get_child())
            __widget__.add(sw)
        
        i = 0
        for move, wins, draws, loses in openings:
            games = wins+draws+loses
            if not games: continue
            wins,draws,loses = map(lambda x: x/float(games), (wins,draws,loses))
            store.append ([move, str(games), (wins,draws,loses)])
    gobject.idle_add(helper)

from Utils.Move import parseSAN, movePool

def selection_changed (widget):
    if len(board.history) != board.shown+1:
        # History/moveparsing model, sucks, sucks, sucks
        board.bluearrow = None
        return
    
    iter = tv.get_selection().get_selected()[1]
    if iter == None:
        board.bluearrow = None
        return
    else: sel = tv.get_model().get_path(iter)[0]
    
    move = parseSAN(board.history[-1], openings[sel][0])
    board.bluearrow = move.cords
    movePool.add(move)

def row_activated (widget, *args):
	arrow = board.bluearrow
	if arrow:
		boardcontrol.emit_move_signal(*arrow)

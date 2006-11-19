import gtk, gobject, cairo
from widgets import gamewidget
from pychess.Utils.book import getOpenings
from pychess.Utils.Move import parseSAN, movePool
from pychess.Utils.const import prefix

__title__ = _("Opening Book")

class Sidepanel:
    
    def load (self, window, page_num):
        widgets = gtk.glade.XML(prefix("sidepanel/book.glade"))
        self.tv = widgets.get_widget("treeview")
        self.sw = widgets.get_widget("scrolledwindow")
        self.sw.unparent()
        
        self.store = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
        self.tv.set_model(self.store)
        
        self.tv.append_column(gtk.TreeViewColumn(
                "Move", gtk.CellRendererText(), text=0))
        r = gtk.CellRendererText()
        r.set_property("xalign", 1)
        self.tv.append_column(gtk.TreeViewColumn("Games", r, text=1))
        self.tv.append_column(gtk.TreeViewColumn(
                "Win/Draw/Loss", window.BookCellRenderer(), data=2))
        
        self.boardcontrol = gamewidget.getWidgets(page_num)[0]
        self.board = self.boardcontrol.view
        self.board.connect("shown_changed", self.shown_changed)
        self.tv.connect("cursor_changed", self.selection_changed)
        self.tv.connect("select_cursor_row", self.selection_changed)
        self.tv.connect("row-activated", self.row_activated)
        
        self.shown_changed(self.board, 0)
        
        return self.sw
    
    def shown_changed (self, board, shown):
        self.openings = getOpenings(self.board.history[-1])
        self.openings.sort(lambda a, b: sum(b[1:])-sum(a[1:]))
        
        self.board.bluearrow = None
        
        def helper():
            self.store.clear()
            
            if not self.openings and self.sw.get_child() == self.tv:
                self.sw.remove(self.tv)
                label = gtk.Label(_("In this position,\nthere is no book move."))
                label.set_property("yalign",0.1)
                self.sw.add_with_viewport(label)
                self.sw.get_child().set_shadow_type(gtk.SHADOW_NONE)
                self.sw.show_all()
                return
            if self.openings and self.sw.get_child() != self.tv:
                self.sw.remove(self.sw.get_child())
                self.sw.add(self.tv)
            
            i = 0
            for move, wins, draws, loses in self.openings:
                games = wins+draws+loses
                if not games: continue
                wins,draws,loses = map(lambda x: x/float(games), (wins,draws,loses))
                self.store.append ([move, str(games), (wins,draws,loses)])
        gobject.idle_add(helper)

    def selection_changed (self, widget):
        if len(self.board.history) != self.board.shown+1:
            # History/moveparsing model, sucks, sucks, sucks
            self.board.bluearrow = None
            return
        
        iter = self.tv.get_selection().get_selected()[1]
        if iter == None:
            self.board.bluearrow = None
            return
        else: sel = self.tv.get_model().get_path(iter)[0]
        
        move = parseSAN(self.board.history[-1], self.openings[sel][0])
        self.board.bluearrow = move.cords
        movePool.add(move)
    
    def row_activated (self, widget, *args):
    	arrow = self.board.bluearrow
    	if arrow:
    		self.boardcontrol.emit_move_signal(*arrow)
    

import gtk, gobject
from gtk import gdk
from pychess.widgets import gamewidget
from pychess.Utils.Move import toSAN
from pychess.Utils.const import prefix

from gtk.gdk import keyval_from_name
leftkeys = map(keyval_from_name,("Left", "KP_Left"))
rightkeys = map(keyval_from_name,("Right", "KP_Right"))

__title__ = _("Move History")
__active__ = True

def fixList (list, xalign=0):
    list.set_model(gtk.ListStore(str))
    renderer = gtk.CellRendererText()
    renderer.set_property("xalign",xalign)
    list.append_column(gtk.TreeViewColumn(None, renderer, text=0))
    list.get_selection().set_mode(gtk.SELECTION_BROWSE)
    
class Sidepanel:
    
    def __init__ (self):
        self.freezed = False
    
    def load (self, window, gmwidg):
        
        widgets = gtk.glade.XML(prefix("sidepanel/history.glade"))
        __widget__ = widgets.get_widget("panel")
        __widget__.unparent()
        
        __active__ = True
        
        self.numbers = widgets.get_widget("treeview1")
        self.left = widgets.get_widget("treeview2")
        self.right = widgets.get_widget("treeview3")

        fixList(self.numbers, 1)
        map(fixList, (self.left, self.right))
        self.numbers.modify_fg(gtk.STATE_INSENSITIVE, gtk.gdk.Color(0,0,0))
        
        self.left.get_selection().connect_after(
                'changed', self.select_cursor_row, self.left, 0)
        self.right.get_selection().connect_after(
                'changed', self.select_cursor_row, self.right, 1)
        
        widgets.signal_autoconnect ({
            "on_treeview2_key_press_event":lambda w,e:self.key_press_event(1,e),
            "on_treeview3_key_press_event":lambda w,e:self.key_press_event(2,e)
        })
        
        self.board = gmwidg.widgets["board"].view
        
        self.board.model.connect("game_changed", self.game_changed)
        self.board.connect("shown_changed", self.shown_changed)
        
        scrollwin = widgets.get_widget("panel")
        
        def changed (vadjust):
            if not hasattr(vadjust, "need_scroll") or vadjust.need_scroll:
                vadjust.set_value(vadjust.upper-vadjust.page_size)
                vadjust.need_scroll = True
        scrollwin.get_vadjustment().connect("changed", changed)
        
        def value_changed (vadjust):
            vadjust.need_scroll = abs(vadjust.value + vadjust.page_size - \
            		vadjust.upper) < vadjust.step_increment
        scrollwin.get_vadjustment().connect("value-changed", value_changed)
        
        return __widget__
    
    def select_cursor_row (self, selection, tree, col):
        iter = selection.get_selected()[1]
        if iter == None: return
        
        if self.freezed: return
        
        row = tree.get_model().get_path(iter)[0]
        if self.board.model.lowply & 1:
            self.board.shown = self.board.model.lowply + row*2 + col
        else: self.board.shown = self.board.model.lowply + row*2 + col +1
    
    def key_press_event (self, col, event):
        if event.keyval in leftkeys:
            self.board.shown -= 1
        elif event.keyval in rightkeys:
            self.board.shown += 1
    
    def game_changed (self, game):
        
        view = game.ply & 1 and self.left or self.right
        other = game.ply & 1 and self.right or self.left
        notat = toSAN(game.boards[-2], game.moves[-1])
        ply = game.ply
        
        def todo():
            if len(view.get_model()) == len(self.numbers.get_model()):
                num = str((ply+1)/2)+"."
                self.numbers.get_model().append([num])
            
            if view == self.right and \
                    len(view.get_model()) == len(other.get_model()):
                self.left.get_model().append([""])
            
            view.get_model().append([notat])
            if self.board.shown < ply or self.freezed:
                return
            
            if game.lowply & 1:
                row = (ply-game.lowply)/2
            else: row = (ply-game.lowply-1)/2
            
            self.freezed = True
            view.get_selection().select_iter(view.get_model().get_iter(row))
            view.set_cursor((row,))
            if other.is_focus():
                view.grab_focus()
            other.get_selection().unselect_all()
            self.freezed = False
        
        gobject.idle_add(todo)
    
    def shown_changed (self, board, shown):
        if shown <= 0:
            self.left.get_selection().unselect_all()
            self.right.get_selection().unselect_all()
            return
        
        col = shown & 1 and self.left or self.right
        other = shown & 1 and self.right or self.left
        
        if self.board.model.lowply & 1:
            row = (shown-self.board.model.lowply)/2
        else: row = (shown-self.board.model.lowply-1)/2
        
        # If game is changed, we can't expect the treeviews to be updated yet.
        # Further more when game_changed is called, it will select stuff it self
        if row >= len(col.get_model()):
            return
        
        if shown > 0:
            col.get_selection().select_iter(col.get_model().get_iter(row))
            col.set_cursor((row,))
            if other.is_focus():
                col.grab_focus()
        other.get_selection().unselect_all()

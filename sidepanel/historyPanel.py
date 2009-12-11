from __future__ import with_statement

import gtk, gobject
from gtk import gdk

from pychess.System import conf
from pychess.System.glock import glock_connect
from pychess.System.prefix import addDataPrefix
from pychess.Utils.Move import toSAN, toFAN

from gtk.gdk import keyval_from_name
leftkeys = map(keyval_from_name,("Left", "KP_Left"))
rightkeys = map(keyval_from_name,("Right", "KP_Right"))

__title__ = _("Move History")
__active__ = True
__icon__ = addDataPrefix("glade/panel_moves.svg")
__desc__ = _("The moves sheet keeps track of the players' moves and lets you navigate through the game history")

class Switch:
    def __init__(self): self.on = False
    def __enter__(self): self.on = True
    def __exit__(self, *a): self.on = False

class Sidepanel:
    
    def __init__ (self):
        self.frozen = Switch()
    
    def load (self, gmwidg):
        
        widgets = gtk.glade.XML(addDataPrefix("sidepanel/history.glade"))
        __widget__ = widgets.get_widget("panel")
        __widget__.unparent()
        
        self.board = gmwidg.board.view
        
        glock_connect(self.board.model, "game_changed", self.game_changed)
        glock_connect(self.board.model, "game_started", self.game_changed)
        glock_connect(self.board.model, "moves_undoing", self.moves_undoing)
        self.board.connect("shown_changed", self.shown_changed)
        
        # Initialize treeviews
        
        self.numbers = widgets.get_widget("treeview1")
        self.left = widgets.get_widget("treeview2")
        self.right = widgets.get_widget("treeview3")
        
        def fixList (list, xalign=0):
            list.set_model(gtk.ListStore(str))
            renderer = gtk.CellRendererText()
            renderer.set_property("xalign",xalign)
            list.append_column(gtk.TreeViewColumn(None, renderer, text=0))
            list.get_selection().set_mode(gtk.SELECTION_SINGLE)
        
        fixList(self.numbers, 1)
        fixList(self.left, 0)
        fixList(self.right, 0)
        
        self.left.get_selection().connect('changed', self.on_selection_changed,
                                          self.left, 0)
        self.right.get_selection().connect('changed', self.on_selection_changed,
                                           self.right, 1)
        
        widgets.signal_autoconnect ({
            "on_treeview2_key_press_event":lambda w,e:self.key_press_event(1,e),
            "on_treeview3_key_press_event":lambda w,e:self.key_press_event(2,e)
        })
        
        # Lock scrolling
        
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
        
        # Connect to preferences
        
        def figuresInNotationCallback (none):
            game = self.board.model
            for board, move in zip(game.boards, game.moves):
                if conf.get("figuresInNotation", False):
                    notat = toFAN(board, move)
                else: notat = toSAN(board, move, True)
                row, col, other = self._ply_to_row_col_other(board.ply+1)
                iter = col.get_model().get_iter((row,))
                col.get_model().set(iter, 0, notat)
        conf.notify_add("figuresInNotation", figuresInNotationCallback)
        
        # Return
        
        return __widget__
    
    def on_selection_changed (self, selection, tree, col):
        iter = selection.get_selected()[1]
        if iter == None: return
        if self.frozen.on: return
        print "sel changed. updating shown"
        row = tree.get_model().get_path(iter)[0]
        if self.board.model.lowply & 1:
            self.board.shown = self.board.model.lowply + row*2 + col
        else: self.board.shown = self.board.model.lowply + row*2 + col +1
    
    def key_press_event (self, col, event):
        if event.keyval in leftkeys:
            self.board.shown -= 1
        elif event.keyval in rightkeys:
            self.board.shown += 1
    
    def moves_undoing (self, game, moves):
        assert game.ply > 0, "Can't undo when ply <= 0"
        for i in xrange(moves):
            try:
                row, view, other = self._ply_to_row_col_other(game.ply-i)
                model = view.get_model()
                model.remove(model.get_iter((row,)))
                if view == self.left:
                    model = self.numbers.get_model()
                    model.remove(model.get_iter((row,)))
            except ValueError:
                continue
    
    def game_changed (self, game):
        len_ = len(self.left.get_model()) + len(self.right.get_model()) + 1
        if len(self.left.get_model()) and not self.left.get_model()[0][0]:
            len_ -= 1
        for ply in xrange(len_+game.lowply, game.ply+1):
            self.__addMove(game, ply)
    
    def __addMove(self, game, ply):
        print "Am I doing anything?"
        row, view, other = self._ply_to_row_col_other(ply)
        
        if conf.get("figuresInNotation", False):
            notat = toFAN(game.getBoardAtPly(ply-1), game.getMoveAtPly(ply-1))
        else: notat = toSAN(game.getBoardAtPly(ply-1), game.getMoveAtPly(ply-1),
                localRepr=True)
        
        # Test if the row is 'filled'
        if len(view.get_model()) == len(self.numbers.get_model()):
            num = str((ply+1)/2)+"."
            self.numbers.get_model().append([num])
        
        # Test if the move is black first move. This will be the case if the
        # game was loaded from a fen/epd starting at black
        if view == self.right and len(view.get_model()) == len(other.get_model()):
            self.left.get_model().append([""])
        
        view.get_model().append([notat])
    
    def shown_changed (self, board, shown):
        if shown <= board.model.lowply:
            print "Or is it me?"
            self.left.get_selection().unselect_all()
            self.right.get_selection().unselect_all()
            return
        print "shown changed", shown 
        row, col, other = self._ply_to_row_col_other(shown)
        
        with self.frozen:
            other.get_selection().unselect_all()
            col.get_selection().select_iter(col.get_model().get_iter(row))
            col.set_cursor((row,))
            col.scroll_to_cell((row,), None, False)
            col.grab_focus()
    
    def _ply_to_row_col_other (self, ply):
        col = ply & 1 and self.left or self.right
        other = ply & 1 and self.right or self.left
        if self.board.model.lowply & 1:
            row = (ply-self.board.model.lowply) // 2
        else: row = (ply-self.board.model.lowply-1) // 2
        return row, col, other

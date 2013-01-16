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
        
        widgets = gtk.Builder()
        widgets.add_from_file(addDataPrefix("sidepanel/history.glade"))
        __widget__ = widgets.get_object("panel")
        __widget__.unparent()
        
        self.boardview = gmwidg.board.view
        
        glock_connect(self.boardview.model, "game_changed", self.game_changed)
        glock_connect(self.boardview.model, "game_started", self.game_changed)
        glock_connect(self.boardview.model, "moves_undoing", self.moves_undoing)
        self.boardview.connect("shown_changed", self.shown_changed)
        
        # Initialize treeviews
        
        self.numbers = widgets.get_object("treeview1")
        self.left = widgets.get_object("treeview2")
        self.right = widgets.get_object("treeview3")
        
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
        
        widgets.connect_signals ({
            "on_treeview2_key_press_event":lambda w,e:self.key_press_event(1,e),
            "on_treeview3_key_press_event":lambda w,e:self.key_press_event(2,e)
        })
        
        # Lock scrolling
        
        scrollwin = widgets.get_object("panel")
        
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
            game = self.boardview.model
            for board, move in zip(game.variations[0], game.moves):
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

        row = tree.get_model().get_path(iter)[0]
        if self.boardview.model.lowply & 1:
            ply = row*2 + col
        else:
            ply = row*2 + col +1
        
        board = self.boardview.model.boards[ply]
        self.boardview.setShownBoard(board)
    
    def key_press_event (self, col, event):
        if event.keyval in leftkeys:
            self.boardview.shown -= 1
        elif event.keyval in rightkeys:
            self.boardview.shown += 1
    
    def moves_undoing (self, game, moves):
        assert game.ply > 0, "Can't undo when ply <= 0"
        for i in xrange(moves):
            try:
                row, view, other = self._ply_to_row_col_other(game.variations[0][-1].ply-i)
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
        #print "Am I doing anything?"
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
    
    def shown_changed (self, boardview, shown):
        if not boardview.inMainLine():
            return
        if shown <= boardview.model.lowply:
            #print "Or is it me?"
            self.left.get_selection().unselect_all()
            self.right.get_selection().unselect_all()
            return
            
        row, col, other = self._ply_to_row_col_other(shown)

        with self.frozen:
            other.get_selection().unselect_all()
            try:
                col.get_selection().select_iter(col.get_model().get_iter(row))
                col.set_cursor((row,))
                col.scroll_to_cell((row,), None, False)
                col.grab_focus()
            except ValueError:
                pass
                # deleted variations by moves_undoing
    
    def _ply_to_row_col_other (self, ply):
        col = ply & 1 and self.left or self.right
        other = ply & 1 and self.right or self.left
        if self.boardview.model.lowply & 1:
            row = (ply-self.boardview.model.lowply) // 2
        else: row = (ply-self.boardview.model.lowply-1) // 2
        return row, col, other

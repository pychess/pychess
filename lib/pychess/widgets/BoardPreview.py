# -*- coding: UTF-8 -*-

import os
import gtk, gtk.glade, gobject
from pychess.Utils.const import reprResult, BLACK, FEN_EMPTY
from pychess.Utils.Board import Board
from pychess.System.uistuff import GladeWidgets
from pychess.System.protoopen import protoopen, splitUri
from pychess.widgets.BoardView import BoardView
from pychess.Savers.ChessFile import LoadingError

def ellipsize (string, maxlen):
    if len(string) <= maxlen or maxlen < 4:
        return string
    return string[:maxlen-3] + "..."

class BoardPreview:
    
    def __init__ (self, widgets, fcbutton, opendialog, enddir):
        self.position = 0
        self.gameno = 0
        self.filename = None
        self.chessfile = None
        
        self.widgets = widgets
        self.fcbutton = fcbutton
        self.enddir = enddir
        
        # Treeview
        self.list = self.widgets["gamesTree"]
        self.list.set_model(gtk.ListStore(str,str,str))
        # GTK_SELECTION_BROWSE - exactly one item is always selected
        self.list.get_selection().set_mode(gtk.SELECTION_BROWSE)
        self.list.get_selection().connect_after(
                'changed', self.on_selection_changed)
        
        # Add columns
        renderer = gtk.CellRendererText()
        renderer.set_property("xalign",0)
        self.list.append_column(gtk.TreeViewColumn(None, renderer, text=0))
        
        self.list.append_column(gtk.TreeViewColumn(None, renderer, text=1))
        
        renderer = gtk.CellRendererText()
        renderer.set_property("xalign",1)
        self.list.append_column(gtk.TreeViewColumn(None, renderer, text=2))
        
        # Connect buttons
        self.widgets["first_button"].connect("clicked", self.on_first_button)
        self.widgets["back_button"].connect("clicked", self.on_back_button)
        self.widgets["forward_button"].connect("clicked", self.on_forward_button)
        self.widgets["last_button"].connect("clicked", self.on_last_button)
        
        # Add the board
        self.boardview = BoardView()
        self.boardview.set_size_request(170,170)
        self.widgets["boardPreviewDock"].add(self.boardview)
        self.boardview.show()
        self.gamemodel = self.boardview.model
        self.boardview.gotStarted = True
        
        # Connect label showing possition
        self.boardview.connect('shown_changed', self.shown_changed)
        self.boardview.autoUpdateShown = False
        
        # Add the filechooserbutton
        self.widgets["fileChooserDock"].add(fcbutton)
        # Connect doubleclicking a file to on_file_activated
        fcbutton.connect("file-activated", self.on_file_activated)
        # Connect the openbutton in the dialog to on_file_activated
        openbut = opendialog.get_children()[0].get_children()[1].get_children()[0]
        openbut.connect("clicked", self.on_file_activated)
        
        # The first time the button is opened, the player has just opened
        # his/her file, before we connected the dialog.
        if self._retrieve_filename():
            self.on_file_activated(fcbutton)
    
    def on_file_activated (self, *args):
        filename = self._retrieve_filename()
        if filename:
            if filename == self.get_filename():
                return
            self.set_filename(filename)
        elif self.get_filename():
            filename = self.get_filename()
        else:
            return
        if os.path.isdir(filename):
            return
        
        ending = filename[filename.rfind(".")+1:]
        loader = self.enddir[ending]
        self.chessfile = chessfile = loader.load(protoopen(filename))
        
        self.list.get_model().clear()
        for gameno in range(len(chessfile)):
            names = chessfile.get_player_names (gameno)
            names = [ellipsize (name, 9) for name in names]
            result = reprResult[chessfile.get_result (gameno)]
            result = result.replace("1/2","½")
            self.list.get_model().append (names+[result])
        
        self.lastSel = -1 # The row that was last selected
        self.list.set_cursor((0,))
    
    def on_selection_changed (self, selection):
        iter = selection.get_selected()[1]
        if iter == None:
            self.gamemodel.boards = [Board(FEN_EMPTY)]
            del self.gamemodel.moves[:]
            self.boardview.shown = 0
            self.boardview.redraw_canvas()
            return
        
        sel = self.list.get_model().get_path(iter)[0]
        if sel == self.lastSel: return
        self.lastSel = sel
        
        self.boardview.animationLock.acquire()
        try:
            try:
                self.chessfile.loadToModel(sel, -1, self.gamemodel)
            except LoadingError, e:
                #TODO: Pressent this a little nicer
                print e
            self.boardview.lastMove = None
            self.boardview._shown = self.gamemodel.lowply
            last = self.gamemodel.ply
        finally:
            self.boardview.animationLock.release()
        self.boardview.redraw_canvas()
        self.boardview.shown = last
    
    def on_first_button (self, button):
        self.boardview.showFirst()
        
    def on_back_button (self, button):
        self.boardview.showPrevious()
        
    def on_forward_button (self, button):
        self.boardview.showNext()
        
    def on_last_button (self, button):
        self.boardview.showLast()
    
    def shown_changed (self, boardView, shown):
        pos = "%d." % (shown/2+1)
        if shown & 1:
            pos += ".."
        self.widgets["posLabel"].set_text(pos)
    
    def set_filename (self, filename):
        asPath = splitUri(filename)[-1]
        if os.path.isfile(asPath):
            self.fcbutton.show()
            if filename != self._retrieve_filename():
                self.fcbutton.set_filename(os.path.abspath(asPath))
        else:
            self.fcbutton.set_uri("")
            self.fcbutton.hide()
        self.filename = filename
    
    def get_filename (self):
        return self.filename
    
    def is_empty (self):
        return not self.chessfile or not len(self.chessfile)
    
    def _retrieve_filename (self):
        #if self.fcbutton.get_filename():
        #    return self.fcbutton.get_filename()
        if self.fcbutton.get_preview_filename():
            return self.fcbutton.get_preview_filename()
        elif self.fcbutton.get_uri():
            return self.fcbutton.get_uri()[7:]
    
    def get_position (self):
        return self.boardview.shown
    
    def get_gameno (self):
        iter = self.list.get_selection().get_selected()[1]
        if iter == None: return -1
        return self.list.get_model().get_path(iter)[0]

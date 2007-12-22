# -*- coding: UTF-8 -*-

import gtk, gtk.glade
from time import sleep
from pychess.Utils.const import reprResult, BLACK
from pychess.System.uistuff import GladeWidgets
from pychess.System.protoopen import protoopen
from pychess.widgets.BoardView import BoardView
from pychess.Savers.ChessFile import LoadingError

def ellipsize (string, maxlen):
    if len(string) <= maxlen or maxlen < 4:
        return string
    return string[:maxlen-3] + "..."

class BoardPreview (gtk.Alignment):
    
    def __init__ (self):
        gtk.Alignment.__init__(self)
        self.position = 0
        self.gameno = 0
        self.uri = None
        self.chessfile = None
        
        # Initing glade
        
        gtk.glade.set_custom_handler(self.widgetHandler)
        self.widgets = GladeWidgets("gamepreview.glade")
        
        # Treeview
        
        self.list = self.widgets["treeview"]
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
        
        # Connect label showing possition
        
        self.widgets["BoardView"].connect('shown_changed', self.shown_changed)
        self.widgets["BoardView"].autoUpdateShown = False
        self.gamemodel = self.widgets["BoardView"].model
        
        # Adding glade widget to self
        
        mainvbox = self.widgets["mainvbox"]
        #self.widgets["mainvbox"].unparent()
        mainvbox.get_parent().remove(mainvbox)
        self.add(mainvbox)
        #self.widgets["mainvbox"].reparent(self)
        self.show_all()
    
    def widgetHandler (self, glade, functionName, widgetName, s1, s2, i1, i2):
        """ Returns the custom widget of the glade file.
            It could be done more fancy, but we do only have one custom widget """
        bv = BoardView()
        bv.set_size_request(170,170)
        return bv
    
    def addFileChooserButton (self, fcbutton, opendialog, enddir):
        if self.widgets["ngfcalignment"].get_children():
            childbut = self.widgets["ngfcalignment"].children()[0]
            self.widgets["ngfcalignment"].remove(childbut)
        
        self.widgets["ngfcalignment"].add(fcbutton)
        self.opendialog = opendialog
        self.enddir = enddir
        
        # Connect doubleclicking a file to on_file_activated
        opendialog.connect("file-activated", self.on_file_activated)
        # Connect the openbutton in the dialog to on_file_activated
        openbut = opendialog.get_children()[0].get_children()[1].get_children()[0]
        openbut.connect("clicked", lambda b: self.on_file_activated(opendialog))
        
        # The first time the button is opened, the player has just opened
        # his/her file, before we connected the dialog.
        if opendialog.get_uri():
            self.on_file_activated(opendialog)
    
    def on_file_activated (self, dialog):
        
        uri = self.get_uri()
        if not uri: return
        self.uri = uri
        
        loader = self.enddir[uri[uri.rfind(".")+1:]]
        ending = uri[uri.rfind(".")+1:]
        self.chessfile = chessfile = loader.load(protoopen(uri))
        
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
        if iter == None or not self.chessfile:
            self.widgets["BoardView"].model.clear()
            return
        
        sel = self.list.get_model().get_path(iter)[0]
        if sel == self.lastSel: return
        self.lastSel = sel
        
        try:
            self.chessfile.loadToModel(sel, -1, self.gamemodel)
        except LoadingError, e:
            #TODO: Pressent this a little nicer
            print e
        self.widgets["BoardView"].showLast()
    
    def on_first_button (self, button):
        self.widgets["BoardView"].showFirst()
        
    def on_back_button (self, button):
        self.widgets["BoardView"].showPrevious()
        
    def on_forward_button (self, button):
        self.widgets["BoardView"].showNext()
        
    def on_last_button (self, button):
        self.widgets["BoardView"].showLast()
    
    def shown_changed (self, boardView, shown):
        pos = "%d." % (shown/2+1)
        if shown & 1:
            pos += ".."
        self.widgets["posLabel"].set_text(pos)
    
    def get_uri (self):
        if self.opendialog.get_preview_filename():
            return "file://" + self.opendialog.get_preview_filename()
        elif self.opendialog.get_uri():
            return self.opendialog.get_uri()
        else: return self.uri
    
    def get_position (self):
        return self.widgets["BoardView"].shown
    
    def get_gameno (self):
        iter = self.list.get_selection().get_selected()[1]
        if iter == None: return -1
        return self.list.get_model().get_path(iter)[0]

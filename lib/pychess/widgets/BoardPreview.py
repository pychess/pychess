# -*- coding: UTF-8 -*-

import gtk, gtk.glade
from gobject import idle_add
from time import sleep
from pychess.Utils.const import prefix, reprResult, BLACK
from pychess.System.WidgetDic import WidgetDic
from pychess.System.protoopen import protoopen
from pychess.widgets.BoardView import BoardView

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
        gladexml = gtk.glade.XML(prefix("glade/gamepreview.glade"))
        self.widgets = WidgetDic(gladexml)
        
        # Treeview
        
        self.list = self.widgets["treeview"]
        self.list.set_model(gtk.ListStore(str,str,str))
        # GTK_SELECTION_BROWSE - exactly one item is always selected
        self.list.get_selection().set_mode(gtk.SELECTION_BROWSE)
        self.list.get_selection().connect_after('changed', self.on_selection_changed)
        
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
        
        # Adding glade widget to self
        
        self.widgets["mainvbox"].unparent()
        self.add(self.widgets["mainvbox"])
        self.show_all()
    
    def widgetHandler (self, glade, functionName, widgetName, s1, s2, i1, i2):
        """ Returns the custom widget of the glade file.
            It could be done more fancy, but we do only have one custom widget """
        bv = BoardView()
        bv.set_size_request(170,170)
        return bv
    
    def addFileChooserButton (self, fcbutton, opendialog, enddir):
        
        # Well, this will crash if method runned twice...
        self.widgets["ngfcalignment"].add(fcbutton)
        self.opendialog = opendialog
        opendialog.connect("file-activated", self.on_file_activated, enddir)
        openbut = opendialog.get_children()[0].get_children()[1].get_children()[0]
        openbut.connect("clicked", lambda b:
            self.on_file_activated(opendialog, enddir))
        
    def on_file_activated (self, dialog, enddir):
        
        uri = self.get_uri()
        if not uri: return
        self.uri = uri
        
        loader = enddir[uri[uri.rfind(".")+1:]]
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
            self.widgets["BoardView"].history.reset()
            return
        
        sel = self.list.get_model().get_path(iter)[0]
        if sel == self.lastSel: return
        self.lastSel = sel
        
        self.widgets["BoardView"].autoUpdateShown = False
        self.widgets["BoardView"].history.reset()
   
        self.chessfile.loadToHistory(sel, -1, self.widgets["BoardView"].history)
        
        self.widgets["BoardView"].autoUpdateShown = True
        # As the event might have been sent before everything in the dialog was
        # painted, we have to wait for self.widgets["BoardView"].square to
        # initialize. Ugly? - sure
        def do():
            if not self.widgets["BoardView"].square:
                sleep(0.05)
                return True
            self.widgets["BoardView"].shown = \
                    len(self.widgets["BoardView"].history)-1
        idle_add(do)
        
    def on_first_button (self, button):
        self.widgets["BoardView"].shown = 0
        
    def on_back_button (self, button):
        self.widgets["BoardView"].shown -= 1
        
    def on_forward_button (self, button):
        self.widgets["BoardView"].shown += 1
        
    def on_last_button (self, button):
        self.widgets["BoardView"].shown = \
            len(self.widgets["BoardView"].history)-1
    
    def shown_changed (self, boardView, shown):
        pos = str((shown-1)/2+1) + "."
        if len(boardView.history) % 2 != shown % 2 and \
                boardView.history.curCol() != BLACK:
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

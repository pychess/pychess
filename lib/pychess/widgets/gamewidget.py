
################################################################################
#                                                                              #
#   This module handles the tabbed layout in PyChess                           #
#                                                                              #
################################################################################

#------------------------------------------------------------------------------#
#                                                                              #
# mainbook(Notebook)                                                           #
#                                                                              #
#------------------------------------------------------------------------------#
#                                                                              #
# mvbox(VBox)                                                                  #
#                                                                              #
#---------------------------------------#--------------------------------------#
#                                       #                                      #
# Alignment                             # HBox                                 #
#                                       #                                      #
#---------------------------------------#-------------------#------------------#
#                                       #                   #                  #
# HBox                                  # VBox              # Statusbar        #
#                                       #                   #                  #
#-------------------#-------------------#---------#---------#------------------#
#                   #                   #         #         #
# lvbox(VBox)       # rvbox(VBox)       # HSepera # HBox    #
#                   #                   #         #         #
#---------#---------#---------#---------#---------#---------#
#         #         #         #         #         #         #
# Alignme # BoardCo # Alignme # Noteboo #         # buttons #
#         #         #         #         #         #         #
#---------#---------#---------#---------#         #---------#
#         #         #         #         #
# ChessCl # BoardVi # HBox    # Panels  #
#         #         #         #         #
#---------#---------#----#----#---------#
                    #pane#clos#
                    #comb#butt#
                    #obox#on  #
                    #----#----#

################################################################################
# Initialize general variables and functions                                   #
################################################################################

widgets = None
def set_widgets (w):
    global widgets
    widgets = w

from threading import Condition

import gtk, os, gobject, glob
from gtk import ICON_LOOKUP_USE_BUILTIN

from pychess.System import glock, myconf, gstreamer
from pychess.Utils.const import prefix, SOUND_BEEP, SOUND_URI
from ChessClock import ChessClock
from BoardControl import BoardControl
from ToggleComboBox import ToggleComboBox

icons = gtk.icon_theme_get_default()
try:
    light_on = icons.load_icon("stock_3d-light-on", 16, ICON_LOOKUP_USE_BUILTIN)
    light_off = icons.load_icon("stock_3d-light-off", 16, ICON_LOOKUP_USE_BUILTIN)
except:
    light_on = icons.load_icon("weather-clear", 16, ICON_LOOKUP_USE_BUILTIN)
    light_off = icons.load_icon("weather-clear-night", 16, ICON_LOOKUP_USE_BUILTIN)
gtk_close = icons.load_icon("gtk-close", 16, ICON_LOOKUP_USE_BUILTIN)
gtk_close20 = icons.load_icon("gtk-close", 20, ICON_LOOKUP_USE_BUILTIN)

media_previous = icons.load_icon("stock_media-prev", 16, ICON_LOOKUP_USE_BUILTIN)
media_rewind = icons.load_icon("stock_media-rew", 16, ICON_LOOKUP_USE_BUILTIN)
media_forward = icons.load_icon("stock_media-fwd", 16, ICON_LOOKUP_USE_BUILTIN)
media_next = icons.load_icon("stock_media-next", 16, ICON_LOOKUP_USE_BUILTIN)

def createImage (pixbuf):
    image = gtk.Image()
    image.set_from_pixbuf(pixbuf)
    return image

def createAlignment (top, right, bottom, left):
    align = gtk.Alignment(.5, .5, 1, 1)
    align.set_property("top-padding", top)
    align.set_property("right-padding", right)
    align.set_property("bottom-padding", bottom)
    align.set_property("left-padding", left)
    return align

def tabsCallback (none):
    head = getheadbook()
    if not head: return
    if head.get_n_pages() == 1:
        if myconf.get("hideTabs"):
            show_tabs(False)
        else:
            show_tabs(True)
myconf.notify_add("hideTabs", tabsCallback)

################################################################################
# The holder class for tab releated widgets                                    #
################################################################################

import imp, gobject

head2mainDic = {}

class GameWidget (gobject.GObject):
    
    __gsignals__ = {
        'closed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
        'infront': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
    }
    
    def __init__ (self, gamemodel):
        gobject.GObject.__init__(self)
        
        #
        # Initialize tab label
        #
        
        tabhbox = gtk.HBox()
        tabhbox.set_spacing(4)
        tabhbox.pack_start(createImage(light_off), expand=False)
        
        close_button = gtk.Button()
        close_button.set_property("can-focus", False)
        close_button.add(createImage(gtk_close))
        close_button.set_relief(gtk.RELIEF_NONE)
        close_button.set_size_request(19,18)
        close_button.connect("clicked", lambda w: self.emit("closed"))
        
        tabhbox.pack_end(close_button, expand=False)
        tabhbox.pack_end(gtk.Label(""))
        tabhbox.show_all() # Gtk doesn't show tab labels when the rest is
                           # show_all'ed
        
        #
        # Initialize center
        #
        
        mvbox = gtk.VBox()
        headchild = gtk.HSeparator()
        global head2mainDic
        head2mainDic[headchild] = self
        
        align = createAlignment (3, 2, 4, 2)
        
        hbox = gtk.HBox()
        hbox.set_spacing(4)
        
        lvbox = gtk.VBox()
        lvbox.set_spacing(4)
        
            #
            # Initialize left center - clock and board
            #
        
        ccalign = createAlignment(1,0,0,0)
        cclock = ChessClock()
        ccalign.add(cclock)
        ccalign.set_size_request(-1, 32)
        
        board = BoardControl(gamemodel, getActionMenuItems())
        
        lvbox.pack_start(ccalign, expand=False)
        lvbox.pack_start(board)
        
            #
            # Initialize right box
            #
        
        rvbox = gtk.VBox()
        rvbox.set_spacing(4)
        
        top_align = createAlignment(0,0,0,0)
        top_align.set_size_request(-1, 32)
        
        side_top_hbox = gtk.HBox()
        
        toggle_combox = ToggleComboBox()
        side_closebut = gtk.Button()
        side_closebut.add(createImage(gtk_close20))
        side_closebut.connect("clicked", lambda w: show_side_panel(False))
        side_closebut.set_relief(gtk.RELIEF_NONE)
        
        side_top_hbox.pack_start(toggle_combox)
        side_top_hbox.pack_start(side_closebut, expand=False)
        top_align.add(side_top_hbox)
        
        side_book = gtk.Notebook()
        side_book.set_show_border(False)
        side_book.set_show_tabs(False)
        
        rvbox.pack_start(top_align, expand=False)
        rvbox.pack_start(side_book)
        
        hbox.pack_start(lvbox)
        hbox.pack_start(rvbox, expand=False)
        
        align.add(hbox)
        
            #
            # Initialize statusbar
            #
        
        stat_hbox = gtk.HBox()
        
        page_vbox = gtk.VBox()
        page_vbox.set_spacing(1)
        
        sep = gtk.HSeparator()
        sep.set_size_request(-1, 2)
        page_hbox = gtk.HBox()
        
        startbut = gtk.Button()
        startbut.add(createImage(media_previous))
        startbut.set_relief(gtk.RELIEF_NONE)
        backbut = gtk.Button()
        backbut.add(createImage(media_rewind))
        backbut.set_relief(gtk.RELIEF_NONE)
        forwbut = gtk.Button()
        forwbut.add(createImage(media_forward))
        forwbut.set_relief(gtk.RELIEF_NONE)
        endbut = gtk.Button()
        endbut.add(createImage(media_next))
        endbut.set_relief(gtk.RELIEF_NONE)
        
        startbut.connect("clicked", lambda w: board.view.showFirst())
        backbut.connect("clicked", lambda w: board.view.showPrevious())
        forwbut.connect("clicked", lambda w: board.view.showNext())
        endbut.connect("clicked", lambda w: board.view.showLast())
        
        page_hbox.pack_start(startbut)
        page_hbox.pack_start(backbut)
        page_hbox.pack_start(forwbut)
        page_hbox.pack_start(endbut)
        
        page_vbox.pack_start(sep)
        page_vbox.pack_start(page_hbox)
        
        statusbar = gtk.Statusbar()
        
        stat_hbox.pack_start(page_vbox, expand=False)
        stat_hbox.pack_start(statusbar)
        
        mvbox.pack_start(align)
        mvbox.pack_start(stat_hbox, expand=False)
        
        #
        # Name most common variables
        #
        
        self.widgets = w = {}
        
        w["board"] = board
        w["ccalign"] = ccalign
        w["cclock"] = cclock
        w["sidepanel"] = rvbox
        w["statusbar"] = statusbar
        w["tabhbox"] = tabhbox
        w["close_button"] = close_button
        
        w["mvbox"] = mvbox
        w["headchild"] = headchild
        w["tabhbox"] = tabhbox
        
        #
        # Add sidepanels
        #
        
        glock.acquire()
        try:
            start = 0
            path = prefix("sidepanel")
            pf = "Panel.py"
            panels = [f[:-3] for f in os.listdir(path) if f.endswith(pf)]
            panels = \
                [imp.load_module(f,*imp.find_module(f,[path])) for f in panels]
            
            for panel in panels:
                toggle_combox.addItem(panel.__title__)
                s = panel.Sidepanel()
                num = side_book.append_page(s.load(self))
                if hasattr(panel, "__active__") and panel.__active__:
                    start = num
            
            toggle_combox.connect("changed",
                    lambda w, oldactive: side_book.set_current_page(w.active))
            side_book.set_current_page(start)
            toggle_combox.active = start
        finally:
            glock.release()
    
    
    def setTabReady (self, ready):
        tabhbox = self.widgets["tabhbox"]
        tabhbox.remove(tabhbox.get_children()[0])
        if ready:
            tabhbox.pack_start(createImage(light_on), expand=False)
        else: tabhbox.pack_start(createImage(light_off), expand=False)
        tabhbox.show_all()
    
    def setTabText (self, text):
        tabhbox = self.widgets["tabhbox"]
        tabhbox.get_children()[1].set_text(text)
        
    def getTabText (self):
        tabhbox = self.widgets["tabhbox"]
        return tabhbox[1].get_text()
    
    def status (self, message):
        statusbar = self.widgets["statusbar"]
        
        glock.acquire()
        try:
            statusbar.pop(0)
            if message:
                statusbar.push(0,message)
        finally:
            glock.release()
    
    def bringToFront (self):
        getheadbook().set_current_page (
                getheadbook().page_num(self.widgets["headchild"]) )


################################################################################
# General functions related to all gamewidgets                                 #
################################################################################

def show_side_panel (show):
    if len(head2mainDic) == 0: return
    
    for gmwidg in head2mainDic.values():
        sidepanel = gmwidg.widgets["sidepanel"]
        if show:
            sidepanel.show()
        else:
            alloc = sidepanel.get_allocation().width
            sidepanel.hide()
    
    hbox = widgets["mainvbox"].get_children()[2] \
            .get_nth_page(0).get_children()[0].child
    
    if show:
        if sidepanel.get_allocation().width > 1:
            panelWidth = sidepanel.get_allocation().width + hbox.get_spacing()
        else: panelWidth = sidepanel.get_size_request()[0] + 10
        widgetsSize = widgets["window1"].get_size()
        widgets["window1"].resize(widgetsSize[0]+panelWidth,widgetsSize[1])
        
    else:
        panelWidth = alloc + hbox.get_spacing()
        widgetsSize = widgets["window1"].get_size()
        widgets["window1"].resize(widgetsSize[0]-panelWidth,widgetsSize[1])

def delGameWidget (gmwidg):
    headbook = getheadbook()
    page_num = headbook.page_num(gmwidg.widgets["headchild"])
    headbook.remove_page(page_num)
    vbox = widgets["mainvbox"]
    mainbook = vbox.get_children()[2]
    mainbook.remove_page(page_num)
    del head2mainDic[gmwidg.widgets["headchild"]]
    
    if headbook.get_n_pages() == 1 and myconf.get("hideTabs"):
        show_tabs(False)
    
    if headbook.get_n_pages() == 0:
        vbox.remove(vbox.get_children()[1])
        vbox.remove(mainbook)
        global background
        vbox.pack_end(background)
        background.show()

def createGameWidget (gamemodel):
    gmwidg = GameWidget(gamemodel)
    attachGameWidget (gmwidg)
    return gmwidg

def attachGameWidget (gmwidg):
    vbox = widgets["mainvbox"]
    
    if len(vbox.get_children()) == 2:
        global background
        background = vbox.get_children()[1] 
        vbox.remove(background)
        align = createAlignment (4, 2, 0, 2)
        align.set_property("yscale", 0)
        headbook = gtk.Notebook()
        headbook.set_scrollable(True)
        align.add(headbook)
        
        mainbook = gtk.Notebook()
        mainbook.set_show_tabs(False)
        mainbook.set_show_border(False)
        def callback (widget, page, page_num):
            mainbook.set_current_page(page_num)
        headbook.connect("switch_page", callback)
        try:
            def page_reordered (widget, child, new_page_num):
                mainbook.reorder_child (
                        head2mainDic[child].widgets["mvbox"], new_page_num )
            headbook.connect("page-reordered", page_reordered)
        except TypeError:
            # Unknow signal name is raised by gtk < 2.10
            pass
        
        vbox.pack_start(align, expand=False)
        vbox.pack_start(mainbook)
        
        mainbook.show_all()
        
        if not myconf.get("hideTabs"):
            align.show_all()
    
    headbook = vbox.get_children()[1].child
    headbook.append_page(gmwidg.widgets["headchild"], gmwidg.widgets["tabhbox"])
    try:
        headbook.set_tab_reorderable (gmwidg.widgets["headchild"], True)
    except AttributeError:
        # Object has no attribute 'set_tab_reorderable' is raised by gtk < 2.10
        pass
    
    def callback (notebook, gpointer, page_num):
        if notebook.get_nth_page(page_num) == gmwidg.widgets["headchild"]:
            gmwidg.emit("infront")
    headbook.connect("switch-page", callback)
    
    # We should always show tabs if more than one exists
    if headbook.get_n_pages() == 2:
        show_tabs(True)
    
    mainbook = vbox.get_children()[2]
    mainbook.append_page(gmwidg.widgets["mvbox"], None)
    
    headbook.show_all()
    gmwidg.widgets["mvbox"].show_all()
    
    headbook.set_current_page(-1)
    mainbook.set_current_page(-1)

def cur_gmwidg ():
    headbook = getheadbook()
    headchild = headbook.get_nth_page(headbook.get_current_page())
    return head2mainDic[headchild]

def getheadbook ():
    if len(widgets["mainvbox"].get_children()) == 2:
        # If the headbook hasn't been added yet
        return None
    return widgets["mainvbox"].get_children()[1].child

def getActionMenuItems ():
    dic = {}
    for item in ("call_flag", "draw", "resign",
                 "force_to_move", "undo1", "pause1"):
        dic[item] = widgets[item]
    return dic

def show_tabs (show):
    if show:
        widgets["mainvbox"].get_children()[1].show_all()
    else: widgets["mainvbox"].get_children()[1].hide()


""" This module handles the tabbed layout in PyChess """

import imp, os, atexit
import traceback
import cStringIO

import gtk, gobject
from gtk import ICON_LOOKUP_USE_BUILTIN

from pychess.System.Log import log
from pychess.System import glock, conf, prefix
from ChessClock import ChessClock
from BoardControl import BoardControl
from pydock.PyDockTop import PyDockTop
from pydock.__init__ import CENTER, EAST, SOUTH
from pychess.System.prefix import addHomePrefix
from pychess.System.uistuff import makeYellow

################################################################################
# Initialize modul constants, and a few worker functions                       #
################################################################################

def createAlignment (top, right, bottom, left):
    align = gtk.Alignment(.5, .5, 1, 1)
    align.set_property("top-padding", top)
    align.set_property("right-padding", right)
    align.set_property("bottom-padding", bottom)
    align.set_property("left-padding", left)
    return align

def cleanNotebook ():
    notebook = gtk.Notebook()
    notebook.set_show_tabs(False)
    notebook.set_show_border(False)
    return notebook

icons = gtk.icon_theme_get_default()
def lookup16 (name, alternative=None):
    try:
        return icons.load_icon(name, 16, ICON_LOOKUP_USE_BUILTIN)
    except:
        return icons.load_icon(alternative, 16, ICON_LOOKUP_USE_BUILTIN)

def createImage (pixbuf):
    image = gtk.Image()
    image.set_from_pixbuf(pixbuf)
    return image

light_on = lookup16("stock_3d-light-on", "weather-clear")
light_off = lookup16("stock_3d-light-off", "weather-clear-night")
gtk_close = lookup16("gtk-close")

media_previous = lookup16("gtk-media-previous-ltr")
media_rewind = lookup16("gtk-media-rewind-ltr")
media_forward = lookup16("gtk-media-forward-ltr")
media_next = lookup16("gtk-media-next-ltr")

GAME_MENU_ITEMS = ("save_game1", "save_game_as1", "properties1", "close1")
ACTION_MENU_ITEMS = ("draw", "pause1", "resume1", "undo1", 
                     "call_flag", "resign", "ask_to_move")
VIEW_MENU_ITEMS = ("rotate_board1", "show_sidepanels", "hint_mode", "spy_mode")
MENU_ITEMS = GAME_MENU_ITEMS + ACTION_MENU_ITEMS + VIEW_MENU_ITEMS

path = prefix.addDataPrefix("sidepanel")
postfix = "Panel.py"
files = [f[:-3] for f in os.listdir(path) if f.endswith(postfix)]
sidePanels = [imp.load_module(f, *imp.find_module(f, [path])) for f in files]
pref_sidePanels = []
for panel in sidePanels:
    if conf.get(panel.__name__, True):
        pref_sidePanels.append(panel)

################################################################################
# Initialize module variables                                                  #
################################################################################

widgets = None
def setWidgets (w):
    global widgets
    widgets = w

def getWidgets ():
    return widgets

key2gmwidg = {}
notebooks = {"board": cleanNotebook(),
             "statusbar": cleanNotebook(),
             "messageArea": cleanNotebook()}
for panel in sidePanels:
    notebooks[panel.__name__] = cleanNotebook()

docks = {"board": (gtk.Label("Board"), notebooks["board"])}

################################################################################
# The holder class for tab releated widgets                                    #
################################################################################

class GameWidget (gobject.GObject):
    
    __gsignals__ = {
        'close_clicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()), 
        'infront': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()), 
        'closed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()), 
    }
    
    def __init__ (self, gamemodel):
        gobject.GObject.__init__(self)
        self.gamemodel = gamemodel
        
        tabcontent = self.initTabcontents()
        boardvbox, board, messageSock = self.initBoardAndClock(gamemodel)
        statusbar, stat_hbox = self.initStatusbar(board)
        
        self.tabcontent = tabcontent
        self.board = board
        self.statusbar = statusbar
        
        self.messageSock = messageSock
        self.notebookKey = gtk.Label(); self.notebookKey.set_size_request(0,0)
        self.boardvbox = boardvbox
        self.stat_hbox = stat_hbox
        
        # Some stuff in the sidepanels .load functions might change UI, so we
        # need glock
        # TODO: Really?
        glock.acquire()
        try:
            self.panels = [panel.Sidepanel().load(self) for panel in sidePanels]
        finally:
            glock.release()
    
    def initTabcontents(self):
        tabcontent = createAlignment(gtk.Notebook().props.tab_vborder,0,0,0)
        hbox = gtk.HBox()
        hbox.set_spacing(4)
        hbox.pack_start(createImage(light_off), expand=False)
        close_button = gtk.Button()
        close_button.set_property("can-focus", False)
        close_button.add(createImage(gtk_close))
        close_button.set_relief(gtk.RELIEF_NONE)
        close_button.set_size_request(20, 18)
        close_button.connect("clicked", lambda w: self.emit("close_clicked"))
        hbox.pack_end(close_button, expand=False)
        label = gtk.Label("")
        label.set_alignment(0,.7)
        hbox.pack_end(label)
        tabcontent.add(hbox)
        tabcontent.show_all() # Gtk doesn't show tab labels when the rest is
        return tabcontent
    
    def initBoardAndClock(self, gamemodel):
        boardvbox = gtk.VBox()
        boardvbox.set_spacing(2)
        
        messageSock = createAlignment(0,0,0,0)
        makeYellow(messageSock)
        
        if gamemodel.timemodel:
            ccalign = createAlignment(0, 0, 0, 0)
            cclock = ChessClock()
            cclock.setModel(gamemodel.timemodel)
            ccalign.add(cclock)
            ccalign.set_size_request(-1, 32)
            boardvbox.pack_start(ccalign, expand=False)
        
        actionMenuDic = {}
        for item in ACTION_MENU_ITEMS:
            actionMenuDic[item] = widgets[item]
        
        board = BoardControl(gamemodel, actionMenuDic)
        boardvbox.pack_start(board)
        return boardvbox, board, messageSock
    
    def initStatusbar(self, board):
        def tip (widget, x, y, keyboard_mode, tooltip, text):
            l = gtk.Label(text)
            tooltip.set_custom(l)
            l.show()
            return True
        stat_hbox = gtk.HBox()
        page_vbox = gtk.VBox()
        page_vbox.set_spacing(1)
        sep = gtk.HSeparator()
        sep.set_size_request(-1, 2)
        page_hbox = gtk.HBox()
        startbut = gtk.Button()
        startbut.add(createImage(media_previous))
        startbut.set_relief(gtk.RELIEF_NONE)
        startbut.props.has_tooltip = True
        startbut.connect("query-tooltip", tip, _("Jump to initial position"))
        backbut = gtk.Button()
        backbut.add(createImage(media_rewind))
        backbut.set_relief(gtk.RELIEF_NONE)
        backbut.props.has_tooltip = True
        backbut.connect("query-tooltip", tip, _("Step back one move"))
        forwbut = gtk.Button()
        forwbut.add(createImage(media_forward))
        forwbut.set_relief(gtk.RELIEF_NONE)
        forwbut.props.has_tooltip = True
        forwbut.connect("query-tooltip", tip, _("Step forward one move"))
        endbut = gtk.Button()
        endbut.add(createImage(media_next))
        endbut.set_relief(gtk.RELIEF_NONE)
        endbut.props.has_tooltip = True
        endbut.connect("query-tooltip", tip, _("Jump to latest position"))
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
        return statusbar, stat_hbox
    
    def setLocked (self, locked):
        """ Makes the board insensitive and turns of the tab ready indicator """
        self.board.setLocked(locked)
        self.tabcontent.child.remove(self.tabcontent.child.get_children()[0])
        if not locked:
            self.tabcontent.child.pack_start(createImage(light_on), expand=False)
        else: self.tabcontent.child.pack_start(createImage(light_off), expand=False)
        self.tabcontent.show_all()
    
    def setTabText (self, text):
        self.tabcontent.child.get_children()[1].set_text(text)
    
    def getTabText (self):
        return self.tabcontent.child.get_children()[1].get_text()
    
    def status (self, message):
        glock.acquire()
        try:
            self.statusbar.pop(0)
            if message:
                self.statusbar.push(0, message)
        finally:
            glock.release()
    
    def bringToFront (self):
        getheadbook().set_current_page(self.getPageNumber())
    
    def getPageNumber (self):
        return getheadbook().page_num(self.notebookKey)
    
    def showMessage (self, messageDialog, vertical=False):
        if self.messageSock.child:
            self.messageSock.remove(self.messageSock.child)
        message, separator, hbuttonbox = messageDialog.child.get_children()
        
        if vertical:
            buttonbox = gtk.VButtonBox()
            buttonbox.props.layout_style = gtk.BUTTONBOX_SPREAD
            for button in hbuttonbox.get_children():
                hbuttonbox.remove(button)
                buttonbox.add(button)
        else:
            messageDialog.child.remove(hbuttonbox)
            buttonbox = hbuttonbox
            buttonbox.props.layout_style = gtk.BUTTONBOX_SPREAD
        
        messageDialog.child.remove(message)
        texts = message.get_children()[1]
        message.set_child_packing(texts, False, False, 0, gtk.PACK_START)
        text1, text2 = texts.get_children()
        text1.props.yalign = 1
        text2.props.yalign = 0
        texts.set_child_packing(text1, True, True, 0, gtk.PACK_START)
        texts.set_child_packing(text2, True, True, 0, gtk.PACK_START)
        texts.set_spacing(3)
        message.pack_end(buttonbox, True, True)
        if self.messageSock.child:
            self.messageSock.remove(self.messageSock.child)
        self.messageSock.add(message)
        self.messageSock.show_all()
        if self == cur_gmwidg():
            notebooks["messageArea"].show()
    
    def hideMessage (self):
        self.messageSock.hide()

################################################################################
# Main handling of gamewidgets                                                 #
################################################################################

def delGameWidget (gmwidg):
    """ Remove the widget from the GUI after the game has been terminated """
    gmwidg.emit("closed")
    
    if len(key2gmwidg) == 1:
        getWidgets()["show_sidepanels"].set_active(True)
    
    del key2gmwidg[gmwidg.notebookKey]
    pageNum = gmwidg.getPageNumber()
    headbook = getheadbook()
    
    headbook.remove_page(pageNum)
    for notebook in notebooks.values():
        notebook.remove_page(pageNum)
    
    if headbook.get_n_pages() == 1 and conf.get("hideTabs", False):
        show_tabs(False)
    
    if headbook.get_n_pages() == 0:
        mainvbox = widgets["mainvbox"]
        mainvbox.remove(mainvbox.get_children()[2])
        mainvbox.remove(mainvbox.get_children()[1])
        mainvbox.pack_end(background)
        background.show()

def _ensureReadForGameWidgets ():
    mainvbox = widgets["mainvbox"]
    if len(mainvbox.get_children()) == 3:
        return
    
    global background
    background = widgets["mainvbox"].get_children()[1]
    mainvbox.remove(background)
    
    # Initing headbook
    
    align = createAlignment (4, 4, 0, 4)
    align.set_property("yscale", 0)
    headbook = gtk.Notebook()
    headbook.set_scrollable(True)
    headbook.props.tab_vborder = 0
    align.add(headbook)
    mainvbox.pack_start(align, expand=False)
    show_tabs(not conf.get("hideTabs", False))
    
    # Initing center
    
    centerVBox = gtk.VBox()
    #centerVBox.set_spacing(3)
    #centerVBox.set_border_width(3)
    
    # The message area
    
    centerVBox.pack_start(notebooks["messageArea"], expand=False)
    def callback (notebook, gpointer, page_num):
        notebook.props.visible = notebook.get_nth_page(page_num).child.props.visible
    notebooks["messageArea"].connect("switch-page", callback)
    
    # The dock
    
    global dock, dockAlign
    dock = PyDockTop("main")
    dockAlign = createAlignment(4,4,0,4)
    dockAlign.add(dock)
    centerVBox.pack_start(dockAlign)
    dockAlign.show()
    dock.show()
    
    dockLocation = addHomePrefix("pydock.xml")
    for panel in sidePanels:
        hbox = gtk.HBox()
        pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(panel.__icon__, 16, 16)
        icon = gtk.image_new_from_pixbuf(pixbuf)
        label = gtk.Label(panel.__title__)
        label.set_size_request(0, 0)
        label.set_alignment(0, 1)
        hbox.pack_start(icon, expand=False, fill=False)
        hbox.pack_start(label, expand=True, fill=True)
        hbox.set_spacing(2)
        hbox.show_all()
        
        def cb (widget, x, y, keyboard_mode, tooltip, title, desc, filename):
            table = gtk.Table(2,2)
            table.set_row_spacings(2)
            table.set_col_spacings(6)
            table.set_border_width(4)
            pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(filename, 56, 56)
            image = gtk.image_new_from_pixbuf(pixbuf)
            image.set_alignment(0, 0)
            table.attach(image, 0,1,0,2)
            titleLabel = gtk.Label()
            titleLabel.set_markup("<b>%s</b>" % title)
            titleLabel.set_alignment(0, 0)
            table.attach(titleLabel, 1,2,0,1)
            descLabel = gtk.Label(desc)
            descLabel.props.wrap = True
            table.attach(descLabel, 1,2,1,2)
            tooltip.set_custom(table)
            table.show_all()
            return True
        hbox.props.has_tooltip = True
        hbox.connect("query-tooltip", cb, panel.__title__, panel.__desc__, panel.__icon__)
        
        docks[panel.__name__] = (hbox, notebooks[panel.__name__])
    
    if os.path.isfile(dockLocation):
        try:
            dock.loadFromXML(dockLocation, docks)
        except Exception, e:
            stringio = cStringIO.StringIO()
            traceback.print_exc(file=stringio)
            error = stringio.getvalue()
            log.error("Dock loading error: %s\n%s" % (e, error))
            md = gtk.MessageDialog(widgets["window1"], type=gtk.MESSAGE_ERROR,
                                   buttons=gtk.BUTTONS_CLOSE)
            md.set_markup(_("<b><big>PyChess was unable to load your panel settings</big></b>"))
            md.format_secondary_text(_("Your panel settings have been reset. If this problem repeats, you should report it to the developers"))
            md.run()
            md.hide()
            os.remove(dockLocation)
            for title, panel in docks.values():
                title.unparent()
                panel.unparent()
    
    if not os.path.isfile(dockLocation):
        leaf = dock.dock(docks["board"][1], CENTER, gtk.Label(docks["board"][0]), "board")
        docks["board"][1].show_all()
        leaf.setDockable(False)
        
        # NE
        leaf = leaf.dock(docks["historyPanel"][1], EAST, docks["historyPanel"][0], "historyPanel")
        conf.set("historyPanel", True)
        leaf = leaf.dock(docks["scorePanel"][1], CENTER, docks["scorePanel"][0], "scorePanel")
        conf.set("scorePanel", True)
        
        # SE
        leaf = leaf.dock(docks["bookPanel"][1], SOUTH, docks["bookPanel"][0], "bookPanel")
        conf.set("bookPanel", True)
        leaf = leaf.dock(docks["commentPanel"][1], CENTER, docks["commentPanel"][0], "commentPanel")
        conf.set("commentPanel", True)
        leaf = leaf.dock(docks["chatPanel"][1], CENTER, docks["chatPanel"][0], "chatPanel")
        conf.set("chatPanel", True)
    
    dock.connect("unrealize", lambda dock: dock.saveToXML(dockLocation))
    
    # The status bar
    
    notebooks["statusbar"].set_border_width(4)
    centerVBox.pack_start(notebooks["statusbar"], expand=False)
    mainvbox.pack_start(centerVBox)
    centerVBox.show_all()
    mainvbox.show()
    
    # Connecting headbook to other notebooks
    
    def callback (notebook, gpointer, page_num):
        for notebook in notebooks.values():
            notebook.set_current_page(page_num)
    headbook.connect("switch-page", callback)
    
    if hasattr(headbook, "set_tab_reorderable"):
        def page_reordered (widget, child, new_num, headbook):
            old_num = notebooks["board"].page_num(key2gmwidg[child].board)
            for notebook in notebooks.values():
                notebook.reorder_child(notebook.get_nth_page(old_num), new_num)
        headbook.connect("page-reordered", page_reordered, headbook)

def attachGameWidget (gmwidg):
    _ensureReadForGameWidgets()
    headbook = getheadbook()
    
    key2gmwidg[gmwidg.notebookKey] = gmwidg
    
    headbook.append_page(gmwidg.notebookKey, gmwidg.tabcontent)
    gmwidg.notebookKey.show_all()
    headbook.set_tab_label_packing(gmwidg.notebookKey, True, True, gtk.PACK_START)
    if hasattr(headbook, "set_tab_reorderable"):
        headbook.set_tab_reorderable (gmwidg.notebookKey, True)
    
    def callback (notebook, gpointer, page_num, gmwidg):
        if notebook.get_nth_page(page_num) == gmwidg.notebookKey:
            gmwidg.emit("infront")
    headbook.connect("switch-page", callback, gmwidg)
    gmwidg.emit("infront")
    
    messageSockAlign = createAlignment(4,4,0,4)
    messageSockAlign.show()
    messageSockAlign.add(gmwidg.messageSock)
    notebooks["messageArea"].append_page(messageSockAlign)
    notebooks["board"].append_page(gmwidg.boardvbox)
    gmwidg.boardvbox.show_all()
    for panel, instance in zip(sidePanels, gmwidg.panels):
        notebooks[panel.__name__].append_page(instance)
        instance.show_all()
    notebooks["statusbar"].append_page(gmwidg.stat_hbox)
    gmwidg.stat_hbox.show_all()

    # We should always show tabs if more than one exists
    if headbook.get_n_pages() == 2:
        show_tabs(True)
    
    headbook.set_current_page(-1)

def cur_gmwidg ():
    headbook = getheadbook()
    if headbook == None: return None
    notebookKey = headbook.get_nth_page(headbook.get_current_page())
    return key2gmwidg[notebookKey]

def getheadbook ():
    if len(widgets["mainvbox"].get_children()) == 2:
        # If the headbook hasn't been added yet
        return None
    return widgets["mainvbox"].get_children()[1].child

def zoomToBoard (viewZoomed):
    if viewZoomed:
        notebooks["board"].get_parent().get_parent().zoomUp()
    else:
        notebooks["board"].get_parent().get_parent().zoomDown()

def show_tabs (show):
    if show:
        widgets["mainvbox"].get_children()[1].show_all()
    else: widgets["mainvbox"].get_children()[1].hide()

def tabsCallback (none):
    head = getheadbook()
    if not head: return
    if head.get_n_pages() == 1:
        show_tabs(not conf.get("hideTabs", False))
conf.notify_add("hideTabs", tabsCallback)

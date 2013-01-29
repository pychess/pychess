
""" This module handles the tabbed layout in PyChess """

from BoardControl import BoardControl
from ChessClock import ChessClock
from MenuItemsDict import MenuItemsDict
from pychess.System import glock, conf, prefix
from pychess.System.Log import log
from pychess.System.glock import glock_connect
from pychess.System.prefix import addUserConfigPrefix
from pychess.System.uistuff import makeYellow
from pychess.Utils.GameModel import GameModel
from pychess.Utils.IconLoader import load_icon
from pychess.Utils.const import *
from pychess.Utils.logic import playerHasMatingMaterial, isClaimableDraw
from pychess.ic.ICGameModel import ICGameModel
from pydock.PyDockTop import PyDockTop
from pydock.__init__ import CENTER, EAST, SOUTH
import cStringIO
import gtk
import gobject
import imp
import os
import traceback




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

def createImage (pixbuf):
    image = gtk.Image()
    image.set_from_pixbuf(pixbuf)
    return image

light_on = load_icon(16, "stock_3d-light-on", "weather-clear")
light_off = load_icon(16, "stock_3d-light-off", "weather-clear-night")
gtk_close = load_icon(16, "gtk-close")

media_previous = load_icon(16, "gtk-media-previous-ltr")
media_rewind = load_icon(16, "gtk-media-rewind-ltr")
media_forward = load_icon(16, "gtk-media-forward-ltr")
media_next = load_icon(16, "gtk-media-next-ltr")

path = prefix.addDataPrefix("sidepanel")
postfix = "Panel.py"
files = [f[:-3] for f in os.listdir(path) if f.endswith(postfix)]
sidePanels = [imp.load_module(f, *imp.find_module(f, [path])) for f in files]

dockLocation = addUserConfigPrefix("pydock.xml")

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
        'close_clicked': (gobject.SIGNAL_RUN_FIRST, None, ()), 
        'infront': (gobject.SIGNAL_RUN_FIRST, None, ()),
        'title_changed': (gobject.SIGNAL_RUN_FIRST, None, ()),
        'closed': (gobject.SIGNAL_RUN_FIRST, None, ()),
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
        
        self.menuitems = MenuItemsDict(self)
        gamemodel.connect("game_started", self.game_started)
        gamemodel.connect("game_ended", self.game_ended)
        gamemodel.connect("game_changed", self.game_changed)
        gamemodel.connect("game_paused", self.game_paused)
        gamemodel.connect("game_resumed", self.game_resumed)
        gamemodel.connect("moves_undone", self.moves_undone)
        gamemodel.connect("game_unended", self.game_unended)
        gamemodel.connect("players_changed", self.players_changed)
        gamemodel.connect("analyzer_added", self.analyzer_added)
        gamemodel.connect("analyzer_removed", self.analyzer_removed)
        gamemodel.connect("analyzer_resumed", self.analyzer_resumed)
        gamemodel.connect("analyzer_paused", self.analyzer_paused)
        self.players_changed(gamemodel)
        if gamemodel.timemodel:
            gamemodel.timemodel.connect("zero_reached", self.zero_reached)
        
        board.view.connect("shown_changed", self.shown_changed)
        
        self.analyzer_cids = {}
        
        # Some stuff in the sidepanels .load functions might change UI, so we
        # need glock
        # TODO: Really?
        glock.acquire()
        try:
            self.panels = [panel.Sidepanel().load(self) for panel in sidePanels]
        finally:
            glock.release()
    
    def __del__ (self):
        self.board.__del__()
    
    def _update_menu_abort (self):
        if self.gamemodel.isEngine2EngineGame():
            self.menuitems["abort"].sensitive = True
            self.menuitems["abort"].tooltip = ""
        elif self.gamemodel.isObservationGame():
            self.menuitems["abort"].sensitive = False
        elif isinstance(self.gamemodel, ICGameModel) \
           and self.gamemodel.status in UNFINISHED_STATES:
            if self.gamemodel.ply < 2:
                self.menuitems["abort"].label = _("Abort")
                self.menuitems["abort"].tooltip = \
                    _("This game can be automatically aborted without rating loss because there has not yet been two moves made")
            else:
                self.menuitems["abort"].label = _("Offer Abort")
                self.menuitems["abort"].tooltip = \
                    _("Your opponent must agree to abort the game because there has been two or more moves made")
            self.menuitems["abort"].sensitive = True
        else:
            self.menuitems["abort"].sensitive = False
            self.menuitems["abort"].tooltip = ""

    def _update_menu_adjourn (self):
        self.menuitems["adjourn"].sensitive = \
            isinstance(self.gamemodel, ICGameModel) and \
            self.gamemodel.status in UNFINISHED_STATES and \
            not self.gamemodel.isObservationGame() and \
            not self.gamemodel.hasGuestPlayers()
        
        if isinstance(self.gamemodel, ICGameModel) and \
            self.gamemodel.status in UNFINISHED_STATES and \
            not self.gamemodel.isObservationGame() and \
            self.gamemodel.hasGuestPlayers():
            self.menuitems["adjourn"].tooltip = \
                _("This game can not be adjourned because one or both players are guests")
        else:
            self.menuitems["adjourn"].tooltip = ""

    def _update_menu_draw (self):
        self.menuitems["draw"].sensitive = self.gamemodel.status in UNFINISHED_STATES \
            and not self.gamemodel.isObservationGame()
        
        def can_win (color):
            if self.gamemodel.timemodel:
                return playerHasMatingMaterial(self.gamemodel.boards[-1], color) and \
                    self.gamemodel.timemodel.getPlayerTime(color) > 0
            else:
                return playerHasMatingMaterial(self.gamemodel.boards[-1], color)
        if isClaimableDraw(self.gamemodel.boards[-1]) or not \
                (can_win(self.gamemodel.players[0].color) or \
                 can_win(self.gamemodel.players[1].color)):
            self.menuitems["draw"].label = _("Claim Draw")
        
    def _update_menu_resign (self):
        self.menuitems["resign"].sensitive = self.gamemodel.status in UNFINISHED_STATES \
            and not self.gamemodel.isObservationGame()
    
    def _update_menu_pause_and_resume (self):
        self.menuitems["pause1"].sensitive = self.gamemodel.status == RUNNING \
            and (self.gamemodel.isEngine2EngineGame() or not self.gamemodel.isObservationGame())
        self.menuitems["resume1"].sensitive = self.gamemodel.status == PAUSED \
            and (self.gamemodel.isEngine2EngineGame() or not self.gamemodel.isObservationGame())
        # TODO: if IC game is over and opponent is available, enable Resume
    
    def _update_menu_undo (self):
        if self.gamemodel.isObservationGame():
            self.menuitems["undo1"].sensitive = False
        elif isinstance(self.gamemodel, ICGameModel):
            if self.gamemodel.status in UNFINISHED_STATES and self.gamemodel.ply > 0:
                self.menuitems["undo1"].sensitive = True
            else:
                self.menuitems["undo1"].sensitive = False
        elif self.gamemodel.ply > 0 \
           and self.gamemodel.status in UNDOABLE_STATES + (RUNNING,):
                self.menuitems["undo1"].sensitive = True
        else:
            self.menuitems["undo1"].sensitive = False
    
    def _update_menu_ask_to_move (self):
        if self.gamemodel.isObservationGame():
            self.menuitems["ask_to_move"].sensitive = False
        elif isinstance(self.gamemodel, ICGameModel):
            self.menuitems["ask_to_move"].sensitive = False
        elif self.gamemodel.waitingplayer.__type__ == LOCAL \
           and self.gamemodel.status in UNFINISHED_STATES \
           and self.gamemodel.status != PAUSED:
            self.menuitems["ask_to_move"].sensitive = True
        else:
            self.menuitems["ask_to_move"].sensitive = False

    def _showHolding (self, holding):
        figurines = ["", ""]
        for color in (BLACK, WHITE):
            for piece in holding[color].keys():
                count = holding[color][piece]
                figurines[color] += " " if count==0 else FAN_PIECES[color][piece]*count
        self.status(figurines[BLACK] + "   " + figurines[WHITE])

    def shown_changed (self, boardview, shown):
        if self.gamemodel.boards[-1].variant == CRAZYHOUSECHESS:
            holding = self.gamemodel.getBoardAtPly(shown, boardview.variation).board.holding
            self._showHolding(holding)
    
    def game_started (self, gamemodel):
        self._update_menu_abort()
        self._update_menu_adjourn()
        self._update_menu_draw()
        self._update_menu_pause_and_resume()
        self._update_menu_resign()
        self._update_menu_undo()
        self._update_menu_ask_to_move()
    
    def game_ended (self, gamemodel, reason):
        for item in self.menuitems:
            if item not in self.menuitems.VIEW_MENU_ITEMS:
                self.menuitems[item].sensitive = False
        self._update_menu_undo()
        self._set_arrow(HINT, None)
        self._set_arrow(SPY, None)
        return False
    
    def game_changed (self, gamemodel):
        self._update_menu_abort()
        self._update_menu_ask_to_move()
        self._update_menu_draw()
        self._update_menu_pause_and_resume()
        self._update_menu_undo()
        self._set_arrow(HINT, None)
        self._set_arrow(SPY, None)
        return False
    
    def game_paused (self, gamemodel):
        self._update_menu_pause_and_resume()
        self._update_menu_undo()
        self._update_menu_ask_to_move()
        return False
    
    def game_resumed (self, gamemodel):
        self._update_menu_pause_and_resume()
        self._update_menu_undo()
        self._update_menu_ask_to_move()
        return False
    
    def moves_undone (self, gamemodel, moves):
        self.game_changed(gamemodel)
        return False
    
    def game_unended (self, gamemodel):
        self._update_menu_abort()
        self._update_menu_adjourn()
        self._update_menu_draw()
        self._update_menu_pause_and_resume()
        self._update_menu_resign()
        self._update_menu_undo()
        self._update_menu_ask_to_move()
        return False
    
    def players_changed (self, gamemodel):
        for player in gamemodel.players:
            self.name_changed(player)
            # Notice that this may connect the same player many times. In
            # normal use that shouldn't be a problem.
            glock_connect(player, "name_changed", self.name_changed)
    
    def _set_arrow (self, analyzer_type, coordinates):
        if analyzer_type == HINT:
            arrow = self.board.view._set_greenarrow
        else:
            arrow = self.board.view._set_redarrow
            
        self.board.view.runWhenReady(arrow, coordinates)
    
    def _on_analyze (self, analyzer, analysis, analyzer_type):
        if len(analysis) >= 1 and analysis[0] is not None:
            moves = analysis[0][0]
            if moves and (self.gamemodel.curplayer.__type__ == LOCAL or \
               [player.__type__ for player in self.gamemodel.players] == [REMOTE, REMOTE]):
                self._set_arrow(analyzer_type, moves[0].cords)
            else:
                self._set_arrow(analyzer_type, None)
        return False
    
    def analyzer_added (self, gamemodel, analyzer, analyzer_type):
        self.analyzer_cids[analyzer_type] = \
            analyzer.connect("analyze", self._on_analyze, analyzer_type)
        #self.menuitems[analyzer_type + "_mode"].active = True
        self.menuitems[analyzer_type + "_mode"].sensitive = True
        return False
    
    def analyzer_removed (self, gamemodel, analyzer, analyzer_type):
        self._set_arrow(analyzer_type, None)
        #self.menuitems[analyzer_type + "_mode"].active = False
        self.menuitems[analyzer_type + "_mode"].sensitive = False
        
        try:
            cid = self.analyzer_cids[analyzer_type]
        except IndexError:
            return False
        if analyzer.handler_is_connected(cid):
            analyzer.disconnect(cid)
            
        return False
    
    def analyzer_resumed (self, gamemodel, analyzer, analyzer_type):
        self.menuitems[analyzer_type + "_mode"].active = True
        self._on_analyze(analyzer, analyzer.getAnalysis(), analyzer_type)
        return False
    
    def analyzer_paused (self, gamemodel, analyzer, analyzer_type):
        self.menuitems[analyzer_type + "_mode"].active = False
        self._set_arrow(analyzer_type, None)
        return False
    
    @property
    def display_text (self):
        vs = " " + _("vs") + " "
        if isinstance(self.gamemodel, ICGameModel):
            ficsgame = self.gamemodel.ficsgame
            t = vs.join((ficsgame.wplayer.long_name(game_type=ficsgame.game_type),
                         ficsgame.bplayer.long_name(game_type=ficsgame.game_type)))
        else:
            t = vs.join(map(repr, self.gamemodel.players))
        
        if self.gamemodel.display_text != "":
            t += " " + self.gamemodel.display_text
        return t
    
    def name_changed (self, player):
        newText = self.display_text
        if newText != self.getTabText():
            self.setTabText(newText)
    
    def zero_reached (self, timemodel, color):
        if self.gamemodel.status not in UNFINISHED_STATES: return
        
        if self.gamemodel.players[0].__type__ == LOCAL \
           and self.gamemodel.players[1].__type__ == LOCAL:
            self.menuitems["call_flag"].sensitive = True
            return
        
        for player in self.gamemodel.players:
            opplayercolor = BLACK if player == self.gamemodel.players[WHITE] else WHITE
            if player.__type__ == LOCAL and opplayercolor == color:
                log.debug("gamewidget.zero_reached: LOCAL player=%s, color=%s\n" % \
                          (repr(player), str(color)))
                self.menuitems["call_flag"].sensitive = True
                break
    
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
        """ Makes the board insensitive and turns off the tab ready indicator """
        log.debug("GameWidget.setLocked: %s locked=%s\n" % (self.gamemodel.players, str(locked)))
        self.board.setLocked(locked)
        if not self.tabcontent.get_children(): return
        if len(self.tabcontent.child.get_children()) < 2:
            log.warn("GameWidget.setLocked: Not removing last tabcontent child\n")
            return
        self.tabcontent.child.remove(self.tabcontent.child.get_children()[0])
        if not locked:
            self.tabcontent.child.pack_start(createImage(light_on), expand=False)
        else: self.tabcontent.child.pack_start(createImage(light_off), expand=False)
        self.tabcontent.show_all()
        log.debug("GameWidget.setLocked: %s: returning\n" % self.gamemodel.players)
    
    def setTabText (self, text):
        self.tabcontent.child.get_children()[1].set_text(text)
        self.emit('title_changed')
    
    def getTabText (self):
        return self.tabcontent.child.get_children()[1].get_text()
    
    def status (self, message):
        glock.acquire()
        try:
            self.statusbar.pop(0)
            if message:
                #print "Setting statusbar to \"%s\"" % str(message)
                self.statusbar.push(0, message)
        finally:
            glock.release()
    
    def bringToFront (self):
        getheadbook().set_current_page(self.getPageNumber())
    
    def isInFront(self):
        if not getheadbook(): return False
        return getheadbook().get_current_page() == self.getPageNumber()
    
    def getPageNumber (self):
        return getheadbook().page_num(self.notebookKey)
    
    def showMessage (self, messageDialog, vertical=False):
        if self.messageSock.child:
            self.messageSock.remove(self.messageSock.child)
        
        message = messageDialog.child.get_children()[0]
        hbuttonbox = messageDialog.child.get_children()[-1]
        
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
        if self == cur_gmwidg():
            notebooks["messageArea"].hide()


################################################################################
# Main handling of gamewidgets                                                 #
################################################################################

def splitit(widget):
    if not hasattr(widget, 'get_children'):
        return
    for child in widget.get_children():
        splitit(child)
        widget.remove(child)

def delGameWidget (gmwidg):
    """ Remove the widget from the GUI after the game has been terminated """
    gmwidg.emit("closed")
    
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
        
        centerVBox = mainvbox.get_children()[2]
        for child in centerVBox.get_children():
            centerVBox.remove(child)
        mainvbox.remove(centerVBox)
        mainvbox.remove(mainvbox.get_children()[1])
        
        mainvbox.pack_end(background)
        background.show()
    
    gmwidg.__del__()

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

        # S
        epanel = leaf.dock(docks["engineOutputPanel"][1], SOUTH, docks["engineOutputPanel"][0], "engineOutputPanel")       
        epanel.default_item_height = 60
 
        # NE
        leaf = leaf.dock(docks["annotationPanel"][1], EAST, docks["annotationPanel"][0], "annotationPanel")
        leaf = leaf.dock(docks["historyPanel"][1], CENTER, docks["historyPanel"][0], "historyPanel")
        leaf = leaf.dock(docks["scorePanel"][1], CENTER, docks["scorePanel"][0], "scorePanel")
        
        # SE
        leaf = leaf.dock(docks["bookPanel"][1], SOUTH, docks["bookPanel"][0], "bookPanel")
        leaf = leaf.dock(docks["commentPanel"][1], CENTER, docks["commentPanel"][0], "commentPanel")
        leaf = leaf.dock(docks["chatPanel"][1], CENTER, docks["chatPanel"][0], "chatPanel")
    
    def unrealize (dock):
        # unhide the panel before saving so its configuration is saved correctly
        notebooks["board"].get_parent().get_parent().zoomDown()
        dock.saveToXML(dockLocation)
        dock.__del__()
    dock.connect("unrealize", unrealize)
    
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
            old_num = notebooks["board"].page_num(key2gmwidg[child].boardvbox)
            if old_num == -1:
                log.error('Games and labels are out of sync!')
            else:
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
    headbook.connect_after("switch-page", callback, gmwidg)
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
    
    if headbook.get_n_pages() == 1 and not widgets["show_sidepanels"].get_active():
        zoomToBoard(True)

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
    if not notebooks["board"].get_parent(): return
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

################################################################################
# Handling of the special sidepanels-design-gamewidget used in preferences     #
################################################################################

designGW = None

def showDesignGW():
    global designGW
    if not designGW:
        designGW = GameWidget(GameModel())
    if isDesignGWShown():
        return
    getWidgets()["show_sidepanels"].set_active(True)
    getWidgets()["show_sidepanels"].set_sensitive(False)
    attachGameWidget(designGW)
    
def hideDesignGW():
    if isDesignGWShown():
        delGameWidget(designGW)
    getWidgets()["show_sidepanels"].set_sensitive(True)

def isDesignGWShown():
    return designGW in key2gmwidg.values()

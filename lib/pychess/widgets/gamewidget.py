
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
from pychess.Utils.lutils import lmove
from pychess.Utils.logic import playerHasMatingMaterial, isClaimableDraw
from pychess.ic import get_infobarmessage_content
from pychess.ic.FICSObjects import get_player_tooltip_text
from pychess.ic.ICGameModel import ICGameModel
from pychess.widgets.InfoBar import InfoBar, InfoBarMessage, InfoBarMessageButton
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
        'title_changed': (gobject.SIGNAL_RUN_FIRST, None, (str,)),
        'closed': (gobject.SIGNAL_RUN_FIRST, None, ()),
    }
    
    def __init__ (self, gamemodel):
        gobject.GObject.__init__(self)
        self.gamemodel = gamemodel
        self.cids = {}
        
        tabcontent, white_label, black_label, game_info_label = self.initTabcontents()
        boardvbox, board, infobar, clock = self.initBoardAndClock(gamemodel)
        statusbar, stat_hbox = self.initStatusbar(board)
        
        self.tabcontent = tabcontent
        self.player_name_labels = (white_label, black_label)
        self.game_info_label = game_info_label
        self.board = board
        self.statusbar = statusbar
        self.infobar = infobar
        infobar.connect("hide", self.infobar_hidden)
        self.clock = clock
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
        gamemodel.connect("game_saved", self.game_saved)
        gamemodel.connect("players_changed", self.players_changed)
        gamemodel.connect("analyzer_added", self.analyzer_added)
        gamemodel.connect("analyzer_removed", self.analyzer_removed)
        gamemodel.connect("analyzer_resumed", self.analyzer_resumed)
        gamemodel.connect("analyzer_paused", self.analyzer_paused)
        self.players_changed(gamemodel)
        if self.gamemodel.display_text:
            self.game_info_label.set_text(" " + self.gamemodel.display_text)
        if gamemodel.timed:
            gamemodel.timemodel.connect("zero_reached", self.zero_reached)
        if isinstance(gamemodel, ICGameModel):
            gamemodel.connection.bm.connect("player_lagged", self.player_lagged)
        board.view.connect("shown_changed", self.shown_changed)
        
        # Some stuff in the sidepanels .load functions might change UI, so we
        # need glock
        # TODO: Really?
        glock.acquire()
        try:
            self.panels = [panel.Sidepanel().load(self) for panel in sidePanels]
        finally:
            glock.release()
    
    def _del (self):
        self.board._del()
        
        for obj in self.cids:
            if obj.handler_is_connected(self.cids[obj]):
                log.debug("GameWidget._del: disconnecting %s" % repr(obj))
                obj.disconnect(self.cids[obj])
        self.cids.clear()
    
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
            if self.gamemodel.timed:
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
        def game_is_pausable ():
            if self.gamemodel.isEngine2EngineGame() or \
                (self.gamemodel.hasLocalPlayer() and \
                 (self.gamemodel.isLocalGame() or \
                  (isinstance(self.gamemodel, ICGameModel) and \
                   self.gamemodel.ply > 1))):
                return True
            else:
                return False
        
        self.menuitems["pause1"].sensitive = \
            self.gamemodel.status == RUNNING and game_is_pausable()
        self.menuitems["resume1"].sensitive =  \
            self.gamemodel.status == PAUSED and game_is_pausable()
        # TODO: if IC game is over and game ended in adjournment
        #       and opponent is available, enable Resume
    
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
        # Help crazyhouse testing
        #if self.gamemodel.boards[-1].variant == CRAZYHOUSECHESS:
        #    holding = self.gamemodel.getBoardAtPly(shown, boardview.variation).board.holding
        #    self._showHolding(holding)

        if self.gamemodel.timemodel.hasTimes and \
            (self.gamemodel.endstatus or self.gamemodel.status in (DRAW, WHITEWON, BLACKWON)) and \
            boardview.shownIsMainLine():
            wmovecount, color = divmod(shown + 1, 2)
            bmovecount = wmovecount -1 if color == WHITE else wmovecount
            if self.gamemodel.timemodel.hasBWTimes(bmovecount, wmovecount):
                self.clock.update(wmovecount, bmovecount)
        
    def game_started (self, gamemodel):
        if self.gamemodel.isLocalGame():
            self.menuitems["abort"].label = _("Abort")
        self._update_menu_abort()
        self._update_menu_adjourn()
        self._update_menu_draw()
        if self.gamemodel.isLocalGame():
            self.menuitems["pause1"].label = _("Pause")
            self.menuitems["resume1"].label = _("Resume")
        else:
            self.menuitems["pause1"].label = _("Offer Pause")
            self.menuitems["resume1"].label = _("Offer Resume")
        self._update_menu_pause_and_resume()
        self._update_menu_resign()
        if self.gamemodel.isLocalGame():
            self.menuitems["undo1"].label = _("Undo")
        else:
            self.menuitems["undo1"].label = _("Offer Undo")
        self._update_menu_undo()
        self._update_menu_ask_to_move()

        if not gamemodel.timed and not gamemodel.timemodel.hasTimes:
            self.boardvbox.remove(self.clock.parent)
    
    def game_ended (self, gamemodel, reason):
        for item in self.menuitems:
            if item not in self.menuitems.VIEW_MENU_ITEMS:
                self.menuitems[item].sensitive = False
        self._update_menu_undo()
        self._set_arrow(HINT, None)
        self._set_arrow(SPY, None)
        return False
    
    def game_changed (self, gamemodel):
        '''This runs when the game changes. It updates everything.'''
        self._update_menu_abort()
        self._update_menu_ask_to_move()
        self._update_menu_draw()
        self._update_menu_pause_and_resume()
        self._update_menu_undo()
        for analyzer_type in (HINT, SPY):
            # only clear arrows if analyzer is examining the last position
            if analyzer_type in gamemodel.spectators and \
               gamemodel.spectators[analyzer_type].board == gamemodel.boards[-1]:
                self._set_arrow(analyzer_type, None)
        self.name_changed(gamemodel.players[0]) #We may need to add * to name
        return False
    
    def game_saved(self, gamemodel, uri):
        '''Run when the game is saved. Will remove * from title.'''
        self.name_changed(gamemodel.players[0]) #We may need to remove * in name
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
    
    def _set_arrow (self, analyzer_type, coordinates):
        if self.gamemodel.isPlayingICSGame():
            return

        if analyzer_type == HINT:
            self.board.view._set_greenarrow(coordinates)
        else:
            self.board.view._set_redarrow(coordinates)
            
    def _on_analyze (self, analyzer, analysis, analyzer_type):
        if not self.menuitems[analyzer_type + "_mode"].active:
            return

        if len(analysis) >= 1 and analysis[0] is not None:
            moves = analysis[0][0]
            if moves and (self.gamemodel.curplayer.__type__ == LOCAL or \
               [player.__type__ for player in self.gamemodel.players] == [REMOTE, REMOTE] or \
               self.gamemodel.status not in UNFINISHED_STATES):
                if moves[0].flag == DROP:
                    board = analyzer.board 
                    piece = lmove.FCORD(moves[0].move)
                    color = board.color if analyzer_type == HINT else 1-board.color
                    cord0 = board.getHoldingCord(color, piece)
                    self._set_arrow(analyzer_type, (cord0, moves[0].cord1))
                else:
                    self._set_arrow(analyzer_type, moves[0].cords)
            else:
                self._set_arrow(analyzer_type, None)
        return False
    
    def analyzer_added (self, gamemodel, analyzer, analyzer_type):
        self.cids[analyzer] = \
            analyzer.connect("analyze", self._on_analyze, analyzer_type)
        #self.menuitems[analyzer_type + "_mode"].active = True
        self.menuitems[analyzer_type + "_mode"].sensitive = True
        return False
    
    def analyzer_removed (self, gamemodel, analyzer, analyzer_type):
        self._set_arrow(analyzer_type, None)
        #self.menuitems[analyzer_type + "_mode"].active = False
        self.menuitems[analyzer_type + "_mode"].sensitive = False
        
        try:
            if analyzer.handler_is_connected(self.cids[analyzer]):
                analyzer.disconnect(self.cids[analyzer])
            del self.cids[analyzer]
        except KeyError:
            pass
            
        return False
    
    def analyzer_resumed (self, gamemodel, analyzer, analyzer_type):
        self.menuitems[analyzer_type + "_mode"].active = True
        self._on_analyze(analyzer, analyzer.getAnalysis(), analyzer_type)
        return False
    
    def analyzer_paused (self, gamemodel, analyzer, analyzer_type):
        self.menuitems[analyzer_type + "_mode"].active = False
        self._set_arrow(analyzer_type, None)
        return False
    
    def player_display_text (self, color=WHITE):
        if isinstance(self.gamemodel, ICGameModel):
            return self.gamemodel.ficsplayers[color].long_name(
                game_type=self.gamemodel.ficsgame.game_type)
        else:
            return repr(self.gamemodel.players[color])
    
    @property
    def display_text (self):
        '''This will give you the name of the game.'''
        vs = " " + _("vs") + " "
        t = vs.join((self.player_display_text(color=WHITE),
                     self.player_display_text(color=BLACK)))
        
        if self.gamemodel.display_text:
            t += " " + self.gamemodel.display_text
        return t
        
    def players_changed (self, gamemodel):
        log.debug("GameWidget.players_changed: starting %s" % repr(gamemodel))
        for player in gamemodel.players:
            self.name_changed(player)
            # Notice that this may connect the same player many times. In
            # normal use that shouldn't be a problem.
            glock_connect(player, "name_changed", self.name_changed)
        log.debug("GameWidget.players_changed: returning")
    
    def name_changed (self, player):
        log.debug("GameWidget.name_changed: starting %s" % repr(player))
        color = self.gamemodel.color(player)
        glock.acquire()
        try:
            self.player_name_labels[color].set_text(
                self.player_display_text(color=color))
            if isinstance(self.gamemodel, ICGameModel) and \
                    player.__type__ == REMOTE:
                self.player_name_labels[color].set_tooltip_text(
                    get_player_tooltip_text(self.gamemodel.ficsplayers[color],
                                            show_status=False))
        finally:
            glock.release()
        self.emit('title_changed', self.display_text)
        log.debug("GameWidget.name_changed: returning")
    
    def zero_reached (self, timemodel, color):
        if self.gamemodel.status not in UNFINISHED_STATES: return
        
        if self.gamemodel.players[0].__type__ == LOCAL \
           and self.gamemodel.players[1].__type__ == LOCAL:
            self.menuitems["call_flag"].sensitive = True
            return
        
        for player in self.gamemodel.players:
            opplayercolor = BLACK if player == self.gamemodel.players[WHITE] else WHITE
            if player.__type__ == LOCAL and opplayercolor == color:
                log.debug("gamewidget.zero_reached: LOCAL player=%s, color=%s" % \
                          (repr(player), str(color)))
                self.menuitems["call_flag"].sensitive = True
                break

    def player_lagged (self, bm, player):
        if player in self.gamemodel.ficsplayers:
            content = get_infobarmessage_content(player,
                                                 _(" has lagged for 30 seconds"),
                                                 self.gamemodel.ficsgame.game_type)
            def response_cb (infobar, response, message):
                message.dismiss()
                return False
            message = InfoBarMessage(gtk.MESSAGE_INFO, content, response_cb)
            message.add_button(InfoBarMessageButton(gtk.STOCK_CLOSE,
                                                    gtk.RESPONSE_CANCEL))
            with glock.glock:
                self.showMessage(message)
        return False
    
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
        text_hbox = gtk.HBox()
        white_label = gtk.Label("")
        text_hbox.pack_start(white_label, expand=False)
        text_hbox.pack_start(gtk.Label(" %s " % _("vs")), expand=False)
        black_label = gtk.Label("")
        text_hbox.pack_start(black_label, expand=False)
        gameinfo_label = gtk.Label("")
        text_hbox.pack_start(gameinfo_label, expand=False)
#        label.set_alignment(0,.7)
        hbox.pack_end(text_hbox)
        tabcontent.add(hbox)
        tabcontent.show_all() # Gtk doesn't show tab labels when the rest is
        return tabcontent, white_label, black_label, gameinfo_label
    
    def initBoardAndClock(self, gamemodel):
        boardvbox = gtk.VBox()
        boardvbox.set_spacing(2)
        infobar = InfoBar()
        
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
        return boardvbox, board, infobar, cclock
    
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
        backbut.connect("clicked", lambda w: board.view.showPrev())
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
        log.debug("GameWidget.setLocked: %s locked=%s" % (self.gamemodel.players, str(locked)))
        self.board.setLocked(locked)
        if not self.tabcontent.get_children(): return
        if len(self.tabcontent.child.get_children()) < 2:
            log.warning("GameWidget.setLocked: Not removing last tabcontent child")
            return
        glock.acquire()
        try:
            child = self.tabcontent.child
            if child:
                child.remove(child.get_children()[0])
                if not locked:
                    child.pack_start(createImage(light_on), expand=False)
                else:
                    child.pack_start(createImage(light_off), expand=False)
            self.tabcontent.show_all()
        finally:
            glock.release()
        log.debug("GameWidget.setLocked: %s: returning" % self.gamemodel.players)
    
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
    
    def infobar_hidden (self, infobar):
        if self == cur_gmwidg():
            notebooks["messageArea"].hide()
    
    def showMessage (self, message):
        self.infobar.push_message(message)
        if self == cur_gmwidg():
            notebooks["messageArea"].show()
    
    def replaceMessages (self, message):
        """ Replace all messages with message """
        self.infobar.clear_messages()
        self.showMessage(message)
    
    def clearMessages (self):
        self.infobar.clear_messages()
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
    log.debug("gamewidget.delGameWidget: starting %s" % repr(gmwidg))
    gmwidg.emit("closed")
    
    called_from_preferences = False
    wl = gtk.window_list_toplevels()
    for window in wl:
        if window.is_active() and window == widgets["preferences"]:
            called_from_preferences = True
            break
            
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
        
        if not called_from_preferences:
            # If the last (but not the designGW) gmwidg was closed
            # and we are FICS-ing, present the FICS lounge
            from pychess.ic.ICLogon import dialog
            try:
                dialog.lounge.present()
            except AttributeError:
                pass
    
    gmwidg._del()

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
    def ma_switch_page (notebook, gpointer, page_num):
        notebook.props.visible = notebook.get_nth_page(page_num).child.props.visible
    notebooks["messageArea"].connect("switch-page", ma_switch_page)
    
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
        epanel = leaf.dock(docks["bookPanel"][1], SOUTH, docks["bookPanel"][0],
                           "bookPanel")       
        epanel.default_item_height = 45
        epanel = epanel.dock(docks["engineOutputPanel"][1], CENTER,
                             docks["engineOutputPanel"][0], "engineOutputPanel")
 
        # NE
        leaf = leaf.dock(docks["annotationPanel"][1], EAST,
                         docks["annotationPanel"][0], "annotationPanel")
        leaf = leaf.dock(docks["historyPanel"][1], CENTER,
                         docks["historyPanel"][0], "historyPanel")
        leaf = leaf.dock(docks["scorePanel"][1], CENTER,
                         docks["scorePanel"][0], "scorePanel")
        
        # SE
        leaf = leaf.dock(docks["chatPanel"][1], SOUTH, docks["chatPanel"][0],
                         "chatPanel")
        leaf = leaf.dock(docks["commentPanel"][1], CENTER,
                         docks["commentPanel"][0], "commentPanel")
    
    def unrealize (dock):
        # unhide the panel before saving so its configuration is saved correctly
        notebooks["board"].get_parent().get_parent().zoomDown()
        dock.saveToXML(dockLocation)
        dock._del()
    dock.connect("unrealize", unrealize)
    
    # The status bar
    
    notebooks["statusbar"].set_border_width(4)
    centerVBox.pack_start(notebooks["statusbar"], expand=False)
    mainvbox.pack_start(centerVBox)
    centerVBox.show_all()
    mainvbox.show()
    
    # Connecting headbook to other notebooks
    
    def hb_switch_page (notebook, gpointer, page_num):
        for notebook in notebooks.values():
            notebook.set_current_page(page_num)
    headbook.connect("switch-page", hb_switch_page)
    
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
    log.debug("attachGameWidget: %s" % gmwidg)
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
    
    align = createAlignment(4,4,0,4)
    align.show()
    align.add(gmwidg.infobar)
    notebooks["messageArea"].append_page(align)
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

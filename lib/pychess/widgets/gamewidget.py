""" This module handles the tabbed layout in PyChess """
from __future__ import absolute_import

import imp
import os
import sys
import traceback
import threading
from collections import defaultdict
from threading import currentThread

from gi.repository import Gdk, Gtk, GLib, GObject

from pychess.compat import StringIO
from .BoardControl import BoardControl
from .ChessClock import ChessClock
from .MenuItemsDict import MenuItemsDict
from pychess.Savers import pgn, fen
from pychess.System import conf, prefix

from pychess.System.Log import log
from pychess.System.idle_add import idle_add
from pychess.System.prefix import addUserConfigPrefix
from pychess.Utils.GameModel import GameModel
from pychess.Utils.IconLoader import load_icon, get_pixbuf
from pychess.Utils.const import REMOTE, UNFINISHED_STATES, PAUSED, RUNNING, LOCAL, \
    WHITE, BLACK, ACTION_MENU_ITEMS, DRAW, UNDOABLE_STATES, HINT, SPY, WHITEWON, \
    MENU_ITEMS, BLACKWON, DROP, FAN_PIECES
from pychess.Utils.Move import listToMoves
from pychess.Utils.lutils import lmove
from pychess.Utils.lutils.lmove import ParsingError
from pychess.Utils.logic import playerHasMatingMaterial, isClaimableDraw
from pychess.ic import get_infobarmessage_content, get_infobarmessage_content2
from pychess.ic.FICSObjects import get_player_tooltip_text
from pychess.ic.ICGameModel import ICGameModel
from pychess.widgets.InfoBar import InfoBarNotebook, InfoBarMessage, InfoBarMessageButton
from .pydock.PyDockTop import PyDockTop
from .pydock.__init__ import CENTER, EAST, SOUTH

# ###############################################################################
# Initialize module constants, and a few worker functions                       #
# ###############################################################################


def createAlignment(top, right, bottom, left):
    align = Gtk.Alignment.new(.5, .5, 1, 1)
    align.set_property("top-padding", top)
    align.set_property("right-padding", right)
    align.set_property("bottom-padding", bottom)
    align.set_property("left-padding", left)
    return align


def cleanNotebook(name=None):
    def customGetTabLabelText(child):
        return name

    notebook = Gtk.Notebook()
    if name is not None:
        notebook.set_name(name)
    notebook.get_tab_label_text = customGetTabLabelText
    notebook.set_show_tabs(False)
    notebook.set_show_border(False)
    return notebook


def createImage(pixbuf):
    image = Gtk.Image()
    image.set_from_pixbuf(pixbuf)
    return image


light_on = load_icon(16, "stock_3d-light-on", "weather-clear")
light_off = load_icon(16, "stock_3d-light-off", "weather-clear-night")
gtk_close = load_icon(16, "gtk-close", "window-close")

media_previous = load_icon(24, "gtk-media-previous-ltr", "media-skip-backward")
media_rewind = load_icon(24, "gtk-media-rewind-ltr", "media-seek-backward")
media_forward = load_icon(24, "gtk-media-forward-ltr", "media-seek-forward")
media_next = load_icon(24, "gtk-media-next-ltr", "media-skip-forward")
media_eject = load_icon(24, "player-eject", "media-eject")

path = prefix.addDataPrefix("sidepanel")
postfix = "Panel.py"
files = [f[:-3] for f in os.listdir(path) if f.endswith(postfix)]
sidePanels = [imp.load_module(f, *imp.find_module(f, [path])) for f in files]

dockLocation = addUserConfigPrefix("pydock.xml")

# ###############################################################################
# Initialize module variables                                                  #
# ###############################################################################

widgets = None


def setWidgets(w):
    global widgets
    widgets = w


def getWidgets():
    return widgets


key2gmwidg = {}
key2cid = {}

notebooks = {}
docks = {}


def get_clean_notebooks(mainvbox):
    """ This function is just a workaround to "Segfault on second match" issue
        https://github.com/pychess/pychess/issues/1354
        I think it's caused by Gtk+ 3.20 CSS theming changes
    """
    global notebooks, docks
    if len(mainvbox.get_children()) == 3:
        return notebooks
    else:
        notebooks = {"board": cleanNotebook("board"),
                     "buttons": cleanNotebook("buttons"),
                     "messageArea": cleanNotebook("messageArea")}
        for panel in sidePanels:
            notebooks[panel.__name__] = cleanNotebook(panel.__name__)
        docks = {"board": (Gtk.Label(label="Board"), notebooks["board"])}
        return notebooks

# ###############################################################################
# The holder class for tab releated widgets                                    #
# ###############################################################################


class GameWidget(GObject.GObject):

    __gsignals__ = {
        'game_close_clicked': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'title_changed': (GObject.SignalFlags.RUN_FIRST, None, (str, )),
        'closed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, gamemodel):
        GObject.GObject.__init__(self)
        self.gamemodel = gamemodel
        self.cids = {}
        self.closed = False

        # InfoBarMessage with rematch, undo or observe buttons
        self.game_ended_message = None

        self.tabcontent, white_label, black_label, self.game_info_label = self.initTabcontents()
        self.boardvbox, self.board, self.infobar, self.clock = self.initBoardAndClock(self.gamemodel)
        self.stat_hbox = self.initButtons(self.board)

        self.player_name_labels = (white_label, black_label)
        self.infobar.connect("hide", self.infobar_hidden)

        self.notebookKey = Gtk.Alignment()
        self.menuitems = MenuItemsDict()

        self.gamemodel_cids = [
            self.gamemodel.connect_after("game_started", self.game_started),
            self.gamemodel.connect_after("game_ended", self.game_ended),
            self.gamemodel.connect_after("game_changed", self.game_changed),
            self.gamemodel.connect("game_paused", self.game_paused),
            self.gamemodel.connect("game_resumed", self.game_resumed),
            self.gamemodel.connect("moves_undone", self.moves_undone),
            self.gamemodel.connect("game_unended", self.game_unended),
            self.gamemodel.connect("game_saved", self.game_saved),
            self.gamemodel.connect("players_changed", self.players_changed),
            self.gamemodel.connect("analyzer_added", self.analyzer_added),
            self.gamemodel.connect("analyzer_removed", self.analyzer_removed),
            self.gamemodel.connect("analyzer_resumed", self.analyzer_resumed),
            self.gamemodel.connect("analyzer_paused", self.analyzer_paused),
            self.gamemodel.connect("message_received", self.message_received),
        ]
        self.players_changed(self.gamemodel)

        self.notify_cids = [conf.notify_add("showFICSgameno", self.on_show_fics_gameno), ]

        if self.gamemodel.display_text:
            if isinstance(self.gamemodel, ICGameModel) and conf.get("showFICSgameno", False):
                self.game_info_label.set_text("%s [%s]" % (
                    self.display_text, self.gamemodel.ficsgame.gameno))
            else:
                self.game_info_label.set_text(self.display_text)
        if self.gamemodel.timed:
            self.cids[self.gamemodel.timemodel] = self.gamemodel.timemodel.connect("zero_reached", self.zero_reached)

        self.connections = defaultdict(list)
        if isinstance(self.gamemodel, ICGameModel):
            self.connections[self.gamemodel.connection.bm].append(
                self.gamemodel.connection.bm.connect("player_lagged", self.player_lagged))
            self.connections[self.gamemodel.connection.bm].append(
                self.gamemodel.connection.bm.connect("opp_not_out_of_time", self.opp_not_out_of_time))
        self.cids[self.board.view] = self.board.view.connect("shownChanged", self.shownChanged)

        def do_load_panels(event):
            # self.panels = [panel.Sidepanel().load(self) if panel.__name__ == "bookPanel" else Gtk.ScrolledWindow() for panel in sidePanels]
            self.panels = [panel.Sidepanel().load(self) for panel in sidePanels]
            if event is not None:
                event.set()

        thread = currentThread()
        if thread.name == "MainThread":
            do_load_panels(None)
        else:
            event = threading.Event()
            GLib.idle_add(do_load_panels, event)
            event.wait()

        if isinstance(self.gamemodel, ICGameModel):
            self.gamemodel.gmwidg_ready.set()

    def _del(self):
        for obj in self.cids:
            if obj.handler_is_connected(self.cids[obj]):
                log.debug("GameWidget._del: disconnecting %s" % repr(obj))
                obj.disconnect(self.cids[obj])
        self.cids = {}

        for obj in self.connections:
            for handler_id in self.connections[obj]:
                if obj.handler_is_connected(handler_id):
                    obj.disconnect(handler_id)
        self.connections = {}

        for cid in self.gamemodel_cids:
            self.gamemodel.disconnect(cid)

        for cid in self.notify_cids:
            conf.notify_remove(cid)

        self.board._del()

        if self.game_ended_message is not None:
            self.game_ended_message.callback = None

    def on_show_fics_gameno(self, *args):
        """ Checks the configuration / preferences to see if the FICS
            game number should be displayed next to player names.
        """
        if isinstance(self.gamemodel, ICGameModel) and conf.get("showFICSgameno", False):
            self.game_info_label.set_text(" [%s]" % self.gamemodel.ficsgame.gameno)
        else:
            self.game_info_label.set_text("")

    @idle_add
    def infront(self):
        for menuitem in self.menuitems:
            self.menuitems[menuitem].update()

        for widget in MENU_ITEMS:
            if widget in self.menuitems:
                continue
            elif widget == 'show_sidepanels' and isDesignGWShown():
                getWidgets()[widget].set_property('sensitive', False)
            else:
                getWidgets()[widget].set_property('sensitive', True)

        # Change window title
        getWidgets()['window1'].set_title('%s - PyChess' % self.display_text)

    def _update_menu_abort(self):
        if self.gamemodel.hasEnginePlayer():
            self.menuitems["abort"].sensitive = True
            self.menuitems["abort"].tooltip = ""
        elif self.gamemodel.isObservationGame():
            self.menuitems["abort"].sensitive = False
        elif isinstance(self.gamemodel, ICGameModel) and self.gamemodel.status in UNFINISHED_STATES:
            if self.gamemodel.ply < 2:
                self.menuitems["abort"].label = _("Abort")
                self.menuitems["abort"].tooltip = \
                    _("This game can be automatically aborted without rating loss because \
                      there has not yet been two moves made")
            else:
                self.menuitems["abort"].label = _("Offer Abort")
                self.menuitems["abort"].tooltip = \
                    _("Your opponent must agree to abort the game because there \
                      has been two or more moves made")
            self.menuitems["abort"].sensitive = True
        else:
            self.menuitems["abort"].sensitive = False
            self.menuitems["abort"].tooltip = ""

    def _update_menu_adjourn(self):
        self.menuitems["adjourn"].sensitive = \
            isinstance(self.gamemodel, ICGameModel) and \
            self.gamemodel.status in UNFINISHED_STATES and \
            not self.gamemodel.isObservationGame() and \
            not self.gamemodel.hasGuestPlayers()

        if isinstance(self.gamemodel, ICGameModel) and \
                self.gamemodel.status in UNFINISHED_STATES and \
                not self.gamemodel.isObservationGame() and self.gamemodel.hasGuestPlayers():
            self.menuitems["adjourn"].tooltip = \
                _("This game can not be adjourned because one or both players are guests")
        else:
            self.menuitems["adjourn"].tooltip = ""

    def _update_menu_draw(self):
        self.menuitems["draw"].sensitive = self.gamemodel.status in UNFINISHED_STATES \
            and not self.gamemodel.isObservationGame()

        def can_win(color):
            if self.gamemodel.timed:
                return playerHasMatingMaterial(self.gamemodel.boards[-1], color) and \
                    self.gamemodel.timemodel.getPlayerTime(color) > 0
            else:
                return playerHasMatingMaterial(self.gamemodel.boards[-1],
                                               color)
        if isClaimableDraw(self.gamemodel.boards[-1]) or not \
                (can_win(self.gamemodel.players[0].color) or
                 can_win(self.gamemodel.players[1].color)):
            self.menuitems["draw"].label = _("Claim Draw")

    def _update_menu_resign(self):
        self.menuitems["resign"].sensitive = self.gamemodel.status in UNFINISHED_STATES \
            and not self.gamemodel.isObservationGame()

    def _update_menu_pause_and_resume(self):
        def game_is_pausable():
            if self.gamemodel.isEngine2EngineGame() or \
                (self.gamemodel.hasLocalPlayer() and
                 (self.gamemodel.isLocalGame() or
                  (isinstance(self.gamemodel, ICGameModel) and
                   self.gamemodel.ply > 1))):
                if sys.platform == "win32" and self.gamemodel.hasEnginePlayer(
                ):
                    return False
                else:
                    return True
            else:
                return False

        self.menuitems["pause1"].sensitive = \
            self.gamemodel.status == RUNNING and game_is_pausable()
        self.menuitems["resume1"].sensitive =  \
            self.gamemodel.status == PAUSED and game_is_pausable()
        # TODO: if IC game is over and game ended in adjournment
        #       and opponent is available, enable Resume

    def _update_menu_undo(self):
        if self.gamemodel.isObservationGame():
            self.menuitems["undo1"].sensitive = False
        elif isinstance(self.gamemodel, ICGameModel):
            if self.gamemodel.status in UNFINISHED_STATES and self.gamemodel.ply > 0:
                self.menuitems["undo1"].sensitive = True
            else:
                self.menuitems["undo1"].sensitive = False
        elif self.gamemodel.ply > 0 and self.gamemodel.status in UNDOABLE_STATES + (RUNNING,):
            self.menuitems["undo1"].sensitive = True
        else:
            self.menuitems["undo1"].sensitive = False

    def _update_menu_ask_to_move(self):
        if self.gamemodel.isObservationGame():
            self.menuitems["ask_to_move"].sensitive = False
        elif isinstance(self.gamemodel, ICGameModel):
            self.menuitems["ask_to_move"].sensitive = False
        elif self.gamemodel.waitingplayer.__type__ == LOCAL and self.gamemodel.status \
                in UNFINISHED_STATES and self.gamemodel.status != PAUSED:
            self.menuitems["ask_to_move"].sensitive = True
        else:
            self.menuitems["ask_to_move"].sensitive = False

    def _showHolding(self, holding):
        figurines = ["", ""]
        for color in (BLACK, WHITE):
            for piece in holding[color].keys():
                count = holding[color][piece]
                figurines[color] += " " if count == 0 else FAN_PIECES[color][
                    piece] * count
        print(figurines[BLACK] + "   " + figurines[WHITE])

    def shownChanged(self, boardview, shown):
        # Help crazyhouse testing
        #    if self.gamemodel.boards[-1].variant == CRAZYHOUSECHESS:
        #    holding = self.gamemodel.getBoardAtPly(shown, boardview.variation).board.holding
        #    self._showHolding(holding)

        if self.gamemodel.timemodel.hasTimes and \
            (self.gamemodel.endstatus or self.gamemodel.status in (DRAW, WHITEWON, BLACKWON)) and \
                boardview.shownIsMainLine():
            wmovecount, color = divmod(shown + 1, 2)
            bmovecount = wmovecount - 1 if color == WHITE else wmovecount
            if self.gamemodel.timemodel.hasBWTimes(bmovecount, wmovecount):
                self.clock.update(wmovecount, bmovecount)

    def game_started(self, gamemodel):
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

        if isinstance(gamemodel,
                      ICGameModel) and not gamemodel.isObservationGame():
            for item in self.menuitems:
                if item in self.menuitems.ANAL_MENU_ITEMS:
                    self.menuitems[item].sensitive = False

        if not gamemodel.timed and not gamemodel.timemodel.hasTimes:
            try:
                self.boardvbox.remove(self.clock.get_parent())
            except TypeError:
                # no clock
                pass

    def game_ended(self, gamemodel, reason):
        for item in self.menuitems:
            if item in self.menuitems.ANAL_MENU_ITEMS:
                self.menuitems[item].sensitive = True
            elif item not in self.menuitems.VIEW_MENU_ITEMS:
                self.menuitems[item].sensitive = False
        self._update_menu_undo()
        self._set_arrow(HINT, None)
        self._set_arrow(SPY, None)
        return False

    def game_changed(self, gamemodel, ply):
        '''This runs when the game changes. It updates everything.'''
        self._update_menu_abort()
        self._update_menu_ask_to_move()
        self._update_menu_draw()
        self._update_menu_pause_and_resume()
        self._update_menu_undo()
        if isinstance(gamemodel,
                      ICGameModel):  # on FICS game board change update allob
            if gamemodel.connection is not None:
                allob = 'allob ' + str(gamemodel.ficsgame.gameno)
                gamemodel.connection.client.run_command(allob)

        for analyzer_type in (HINT, SPY):
            # only clear arrows if analyzer is examining the last position
            if analyzer_type in gamemodel.spectators and \
               gamemodel.spectators[analyzer_type].board == gamemodel.boards[-1]:
                self._set_arrow(analyzer_type, None)
        self.name_changed(gamemodel.players[0])  # We may need to add * to name

        if gamemodel.isObservationGame() and not self.isInFront():
            self.light_on_off(True)
        return False

    def game_saved(self, gamemodel, uri):
        '''Run when the game is saved. Will remove * from title.'''
        self.name_changed(gamemodel.players[0])  # We may need to remove * in name
        return False

    def game_paused(self, gamemodel):
        self._update_menu_pause_and_resume()
        self._update_menu_undo()
        self._update_menu_ask_to_move()
        return False

    def game_resumed(self, gamemodel):
        self._update_menu_pause_and_resume()
        self._update_menu_undo()
        self._update_menu_ask_to_move()
        return False

    def moves_undone(self, gamemodel, moves):
        self.game_changed(gamemodel, 0)
        return False

    def game_unended(self, gamemodel):
        self._update_menu_abort()
        self._update_menu_adjourn()
        self._update_menu_draw()
        self._update_menu_pause_and_resume()
        self._update_menu_resign()
        self._update_menu_undo()
        self._update_menu_ask_to_move()
        return False

    def _set_arrow(self, analyzer_type, coordinates):
        if self.gamemodel.isPlayingICSGame():
            return

        if analyzer_type == HINT:
            self.board.view._setGreenarrow(coordinates)
        else:
            self.board.view._setRedarrow(coordinates)

    def _on_analyze(self, analyzer, analysis, analyzer_type):
        if self.board.view.animating:
            return

        if not self.menuitems[analyzer_type + "_mode"].active:
            return

        if len(analysis) >= 1 and analysis[0] is not None:
            movstrs, score, depth = analysis[0]
            board = analyzer.board
            try:
                moves = listToMoves(board, movstrs, validate=True)
            except ParsingError as e:
                # ParsingErrors may happen when parsing "old" lines from
                # analyzing engines, which haven't yet noticed their new tasks
                log.debug("__parseLine: Ignored (%s) from analyzer: ParsingError%s" %
                          (' '.join(movstrs), e))
                return
            except:
                return

            if moves and (self.gamemodel.curplayer.__type__ == LOCAL or
               [player.__type__ for player in self.gamemodel.players] == [REMOTE, REMOTE] or
               self.gamemodel.status not in UNFINISHED_STATES):
                if moves[0].flag == DROP:
                    piece = lmove.FCORD(moves[0].move)
                    color = board.color if analyzer_type == HINT else 1 - board.color
                    cord0 = board.getHoldingCord(color, piece)
                    self._set_arrow(analyzer_type, (cord0, moves[0].cord1))
                else:
                    self._set_arrow(analyzer_type, moves[0].cords)
            else:
                self._set_arrow(analyzer_type, None)
        return False

    def analyzer_added(self, gamemodel, analyzer, analyzer_type):
        self.cids[analyzer] = \
            analyzer.connect("analyze", self._on_analyze, analyzer_type)
        # self.menuitems[analyzer_type + "_mode"].active = True
        self.menuitems[analyzer_type + "_mode"].sensitive = True
        return False

    def analyzer_removed(self, gamemodel, analyzer, analyzer_type):
        self._set_arrow(analyzer_type, None)
        # self.menuitems[analyzer_type + "_mode"].active = False
        self.menuitems[analyzer_type + "_mode"].sensitive = False

        try:
            if analyzer.handler_is_connected(self.cids[analyzer]):
                analyzer.disconnect(self.cids[analyzer])
            del self.cids[analyzer]
        except KeyError:
            pass

        return False

    def analyzer_resumed(self, gamemodel, analyzer, analyzer_type):
        self.menuitems[analyzer_type + "_mode"].active = True
        self._on_analyze(analyzer, analyzer.getAnalysis(), analyzer_type)
        return False

    def analyzer_paused(self, gamemodel, analyzer, analyzer_type):
        self.menuitems[analyzer_type + "_mode"].active = False
        self._set_arrow(analyzer_type, None)
        return False

    def player_display_text(self, color=WHITE):
        if isinstance(self.gamemodel, ICGameModel):
            if self.gamemodel.ficsplayers:
                return self.gamemodel.ficsplayers[color].name
            else:
                return ""
        else:
            if self.gamemodel.players:
                return repr(self.gamemodel.players[color])
            else:
                return ""

    @property
    def display_text(self):
        if not self.gamemodel.players:
            return ""
        '''This will give you the name of the game.'''
        vs = " - "
        t = vs.join((self.player_display_text(color=WHITE),
                     self.player_display_text(color=BLACK)))
        return t

    def players_changed(self, gamemodel):
        log.debug("GameWidget.players_changed: starting %s" % repr(gamemodel))
        for player in gamemodel.players:
            self.name_changed(player)
            # Notice that this may connect the same player many times. In
            # normal use that shouldn't be a problem.
            self.cids[player] = player.connect("name_changed", self.name_changed)
        log.debug("GameWidget.players_changed: returning")

    def name_changed(self, player):
        log.debug("GameWidget.name_changed: starting %s" % repr(player))
        color = self.gamemodel.color(player)

        def do_name_changed():
            if self.gamemodel is None:
                return
            self.player_name_labels[color].set_text(self.player_display_text(
                color=color))
            if isinstance(self.gamemodel, ICGameModel) and \
                    player.__type__ == REMOTE:
                self.player_name_labels[color].set_tooltip_text(
                    get_player_tooltip_text(self.gamemodel.ficsplayers[color],
                                            show_status=False))
        GLib.idle_add(do_name_changed)

        self.emit('title_changed', self.display_text)
        log.debug("GameWidget.name_changed: returning")

    def message_received(self, gamemodel, name, msg):
        if gamemodel.isObservationGame() and not self.isInFront():
            text = self.game_info_label.get_text()
            self.game_info_label.set_markup(
                '<span color="red" weight="bold">%s</span>' % text)

    def zero_reached(self, timemodel, color):
        if self.gamemodel.status not in UNFINISHED_STATES:
            return

        if self.gamemodel.players[0].__type__ == LOCAL \
           and self.gamemodel.players[1].__type__ == LOCAL:
            self.menuitems["call_flag"].sensitive = True
            return

        for player in self.gamemodel.players:
            opplayercolor = BLACK if player == self.gamemodel.players[
                WHITE] else WHITE
            if player.__type__ == LOCAL and opplayercolor == color:
                log.debug("gamewidget.zero_reached: LOCAL player=%s, color=%s" %
                          (repr(player), str(color)))
                self.menuitems["call_flag"].sensitive = True
                break

    @idle_add
    def player_lagged(self, bm, player):
        if player in self.gamemodel.ficsplayers:
            content = get_infobarmessage_content(
                player, _(" has lagged for 30 seconds"),
                self.gamemodel.ficsgame.game_type)

            def response_cb(infobar, response, message):
                message.dismiss()
                return False

            message = InfoBarMessage(Gtk.MessageType.INFO, content,
                                     response_cb)
            message.add_button(InfoBarMessageButton(Gtk.STOCK_CLOSE,
                                                    Gtk.ResponseType.CANCEL))
            self.showMessage(message)
        return False

    @idle_add
    def opp_not_out_of_time(self, bm):
        if self.gamemodel is not None and self.gamemodel.remote_player.time <= 0:
            content = get_infobarmessage_content2(
                self.gamemodel.remote_ficsplayer,
                _(" is lagging heavily but hasn't disconnected"),
                _("Continue to wait for opponent, or try to adjourn the game?"),
                gametype=self.gamemodel.ficsgame.game_type)

            def response_cb(infobar, response, message):
                if response == 2:
                    self.gamemodel.connection.client.run_command("adjourn")
                message.dismiss()
                return False

            message = InfoBarMessage(Gtk.MessageType.QUESTION, content,
                                     response_cb)
            message.add_button(InfoBarMessageButton(
                _("Wait"), Gtk.ResponseType.CANCEL))
            message.add_button(InfoBarMessageButton(_("Adjourn"), 2))
            self.showMessage(message)
        return False

    def on_game_close_clicked(self, button):
        log.debug("gamewidget.on_game_close_clicked %s" % button)
        self.emit("game_close_clicked")

    def initTabcontents(self):
        tabcontent = createAlignment(0, 0, 0, 0)
        hbox = Gtk.HBox()
        hbox.set_spacing(4)
        hbox.pack_start(createImage(light_off), False, True, 0)
        close_button = Gtk.Button()
        close_button.set_property("can-focus", False)
        close_button.add(createImage(gtk_close))
        close_button.set_relief(Gtk.ReliefStyle.NONE)
        close_button.set_size_request(20, 18)

        self.cids[close_button] = close_button.connect("clicked", self.on_game_close_clicked)

        hbox.pack_end(close_button, False, True, 0)
        text_hbox = Gtk.HBox()
        white_label = Gtk.Label(label="")
        text_hbox.pack_start(white_label, False, True, 0)
        text_hbox.pack_start(Gtk.Label(" - "), False, True, 0)
        black_label = Gtk.Label(label="")
        text_hbox.pack_start(black_label, False, True, 0)
        gameinfo_label = Gtk.Label(label="")
        text_hbox.pack_start(gameinfo_label, False, True, 0)
        #        label.set_alignment(0,.7)
        hbox.pack_end(text_hbox, True, True, 0)
        tabcontent.add(hbox)
        tabcontent.show_all()  # Gtk doesn't show tab labels when the rest is
        return tabcontent, white_label, black_label, gameinfo_label

    def initBoardAndClock(self, gamemodel):
        boardvbox = Gtk.VBox()
        boardvbox.set_spacing(2)
        infobar = InfoBarNotebook("gamewidget_infobar")

        ccalign = createAlignment(0, 0, 0, 0)
        cclock = ChessClock()
        cclock.setModel(gamemodel.timemodel)
        ccalign.add(cclock)
        ccalign.set_size_request(-1, 32)
        boardvbox.pack_start(ccalign, False, True, 0)

        actionMenuDic = {}
        for item in ACTION_MENU_ITEMS:
            actionMenuDic[item] = widgets[item]

        board = BoardControl(gamemodel, actionMenuDic)
        boardvbox.pack_start(board, True, True, 0)
        return boardvbox, board, infobar, cclock

    def initButtons(self, board):
        def tip(widget, x, y, keyboard_mode, tooltip, text):
            label = Gtk.Label(label=text)
            tooltip.set_custom(label)
            label.show()
            return True

        align = createAlignment(4, 0, 4, 0)
        page_hbox = Gtk.HBox()
        startbut = Gtk.Button()
        startbut.add(createImage(media_previous))
        startbut.set_relief(Gtk.ReliefStyle.NONE)
        startbut.props.has_tooltip = True
        startbut.connect("query-tooltip", tip, _("Jump to initial position"))
        backbut = Gtk.Button()
        backbut.add(createImage(media_rewind))
        backbut.set_relief(Gtk.ReliefStyle.NONE)
        backbut.props.has_tooltip = True
        backbut.connect("query-tooltip", tip, _("Step back one move"))
        mainbut = Gtk.Button()
        mainbut.add(createImage(media_eject))
        mainbut.set_relief(Gtk.ReliefStyle.NONE)
        mainbut.props.has_tooltip = True
        mainbut.connect("query-tooltip", tip, _("Go back to the main line"))

        forwbut = Gtk.Button()
        forwbut.add(createImage(media_forward))
        forwbut.set_relief(Gtk.ReliefStyle.NONE)
        forwbut.props.has_tooltip = True
        forwbut.connect("query-tooltip", tip, _("Step forward one move"))
        endbut = Gtk.Button()
        endbut.add(createImage(media_next))
        endbut.set_relief(Gtk.ReliefStyle.NONE)
        endbut.props.has_tooltip = True
        endbut.connect("query-tooltip", tip, _("Jump to latest position"))

        def on_clicked(button, func):
            func()
        self.cids[startbut] = startbut.connect("clicked", on_clicked, self.board.view.showFirst)
        self.cids[backbut] = backbut.connect("clicked", on_clicked, self.board.view.showPrev)
        self.cids[mainbut] = mainbut.connect("clicked", on_clicked, self.board.view.backToMainLine)
        self.cids[forwbut] = forwbut.connect("clicked", on_clicked, self.board.view.showNext)
        self.cids[endbut] = endbut.connect("clicked", on_clicked, self.board.view.showLast)
        page_hbox.pack_start(startbut, True, True, 0)
        page_hbox.pack_start(backbut, True, True, 0)
        page_hbox.pack_start(mainbut, True, True, 0)
        page_hbox.pack_start(forwbut, True, True, 0)
        page_hbox.pack_start(endbut, True, True, 0)
        align.add(page_hbox)
        return align

    @idle_add
    def light_on_off(self, on):
        child = self.tabcontent.get_child()
        if child:
            child.remove(child.get_children()[0])
            if on:
                # child.pack_start(createImage(light_on, True, True, 0), expand=False)
                child.pack_start(createImage(light_on), True, True, 0)
            else:
                # child.pack_start(createImage(light_off, True, True, 0), expand=False)
                child.pack_start(createImage(light_off), True, True, 0)
        self.tabcontent.show_all()

    def setLocked(self, locked):
        """ Makes the board insensitive and turns off the tab ready indicator """
        log.debug("GameWidget.setLocked: %s locked=%s" %
                  (self.gamemodel.players, str(locked)))
        self.board.setLocked(locked)
        if not self.tabcontent.get_children():
            return
        if len(self.tabcontent.get_child().get_children()) < 2:
            log.warning(
                "GameWidget.setLocked: Not removing last tabcontent child")
            return

        self.light_on_off(not locked)

        log.debug("GameWidget.setLocked: %s: returning" %
                  self.gamemodel.players)

    def bringToFront(self):
        getheadbook().set_current_page(self.getPageNumber())

    def isInFront(self):
        if not getheadbook():
            return False
        return getheadbook().get_current_page() == self.getPageNumber()

    def getPageNumber(self):
        return getheadbook().page_num(self.notebookKey)

    def infobar_hidden(self, infobar):
        if self == cur_gmwidg():
            notebooks["messageArea"].hide()

    def showMessage(self, message):
        self.infobar.push_message(message)
        if self == cur_gmwidg():
            notebooks["messageArea"].show()

    def replaceMessages(self, message):
        """ Replace all messages with message """
        if not self.closed:
            self.infobar.clear_messages()
            self.showMessage(message)

    def clearMessages(self):
        self.infobar.clear_messages()
        if self == cur_gmwidg():
            notebooks["messageArea"].hide()

    def copy_pgn(self):
        output = StringIO()
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(pgn.save(output, self.gamemodel), -1)

    def copy_fen(self):
        output = StringIO()
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(
            fen.save(output, self.gamemodel, self.board.view.shown), -1)

# ###############################################################################
# Main handling of gamewidgets                                                 #
# ###############################################################################


def splitit(widget):
    if not hasattr(widget, 'get_children'):
        return
    for child in widget.get_children():
        splitit(child)
        widget.remove(child)


def delGameWidget(gmwidg):
    """ Remove the widget from the GUI after the game has been terminated """
    global dock, dockAlign
    log.debug("gamewidget.delGameWidget: starting %s" % repr(gmwidg))
    gmwidg.closed = True
    gmwidg.emit("closed")

    called_from_preferences = False
    # wl = Gtk.window_list_toplevels()
    window_list = Gtk.Window.list_toplevels()
    for window in window_list:
        if window.is_active() and window == widgets["preferences"]:
            called_from_preferences = True
            break

    if gmwidg.notebookKey in key2gmwidg:
        del key2gmwidg[gmwidg.notebookKey]
    pageNum = gmwidg.getPageNumber()
    headbook = getheadbook()

    if gmwidg.notebookKey in key2cid:
        headbook.disconnect(key2cid[gmwidg.notebookKey])
        del key2cid[gmwidg.notebookKey]

    headbook.remove_page(pageNum)
    for notebook in notebooks.values():
        notebook.remove_page(pageNum)

    if headbook.get_n_pages() == 1 and conf.get("hideTabs", False):
        show_tabs(False)

    if headbook.get_n_pages() == 0:
        dock = None
        dockAlign = None
        mainvbox = widgets["mainvbox"]
        centerVBox = mainvbox.get_children()[2]
        for child in centerVBox.get_children():
            centerVBox.remove(child)
        mainvbox.remove(centerVBox)
        mainvbox.remove(mainvbox.get_children()[1])

        mainvbox.pack_end(background, True, True, 0)
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


def _ensureReadForGameWidgets():
    mainvbox = widgets["mainvbox"]
    if len(mainvbox.get_children()) == 3:
        return
    global background, notebooks
    notebooks = get_clean_notebooks(mainvbox)
    background = widgets["mainvbox"].get_children()[1]
    mainvbox.remove(background)

    # Initing headbook

    align = createAlignment(4, 4, 0, 4)
    align.set_property("yscale", 0)
    headbook = Gtk.Notebook()
    headbook.set_scrollable(True)
    align.add(headbook)
    mainvbox.pack_start(align, False, True, 0)
    show_tabs(not conf.get("hideTabs", False))

    # Initing center

    centerVBox = Gtk.VBox()

    # The dock

    global dock, dockAlign
    dock = PyDockTop("main")
    dockAlign = createAlignment(4, 4, 0, 4)
    dockAlign.add(dock)
    centerVBox.pack_start(dockAlign, True, True, 0)
    dockAlign.show()
    dock.show()

    for panel in sidePanels:
        hbox = Gtk.HBox()
        pixbuf = get_pixbuf(panel.__icon__, 16)
        icon = Gtk.Image.new_from_pixbuf(pixbuf)
        label = Gtk.Label(label=panel.__title__)
        label.set_size_request(0, 0)
        label.set_alignment(0, 1)
        hbox.pack_start(icon, False, False, 0)
        hbox.pack_start(label, True, True, 0)
        hbox.set_spacing(2)
        hbox.show_all()

        def cb(widget, x, y, keyboard_mode, tooltip, title, desc, filename):
            table = Gtk.Table(2, 2)
            table.set_row_spacings(2)
            table.set_col_spacings(6)
            table.set_border_width(4)
            pixbuf = get_pixbuf(filename, 56)
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            image.set_alignment(0, 0)
            table.attach(image, 0, 1, 0, 2)
            titleLabel = Gtk.Label()
            titleLabel.set_markup("<b>%s</b>" % title)
            titleLabel.set_alignment(0, 0)
            table.attach(titleLabel, 1, 2, 0, 1)
            descLabel = Gtk.Label(label=desc)
            descLabel.props.wrap = True
            table.attach(descLabel, 1, 2, 1, 2)
            tooltip.set_custom(table)
            table.show_all()
            return True

        hbox.props.has_tooltip = True
        hbox.connect("query-tooltip", cb, panel.__title__, panel.__desc__,
                     panel.__icon__)

        docks[panel.__name__] = (hbox, notebooks[panel.__name__])

    if os.path.isfile(dockLocation):
        try:
            dock.loadFromXML(dockLocation, docks)
        except Exception as e:
            stringio = StringIO()
            traceback.print_exc(file=stringio)
            error = stringio.getvalue()
            log.error("Dock loading error: %s\n%s" % (e, error))
            msg_dia = Gtk.MessageDialog(widgets["window1"],
                                        type=Gtk.MessageType.ERROR,
                                        buttons=Gtk.ButtonsType.CLOSE)
            msg_dia.set_markup(_(
                "<b><big>PyChess was unable to load your panel settings</big></b>"))
            msg_dia.format_secondary_text(_(
                "Your panel settings have been reset. If this problem repeats, \
                you should report it to the developers"))
            msg_dia.run()
            msg_dia.hide()
            os.remove(dockLocation)
            for title, panel in docks.values():
                title.unparent()
                panel.unparent()

    if not os.path.isfile(dockLocation):
        leaf = dock.dock(docks["board"][1],
                         CENTER,
                         Gtk.Label(label=docks["board"][0]),
                         "board")
        docks["board"][1].show_all()
        leaf.setDockable(False)

        # S
        epanel = leaf.dock(docks["bookPanel"][1], SOUTH, docks["bookPanel"][0],
                           "bookPanel")
        epanel.default_item_height = 45
        epanel = epanel.dock(docks["engineOutputPanel"][1], CENTER,
                             docks["engineOutputPanel"][0],
                             "engineOutputPanel")

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

    def unrealize(dock, notebooks):
        # unhide the panel before saving so its configuration is saved correctly
        notebooks["board"].get_parent().get_parent().zoomDown()
        dock.saveToXML(dockLocation)
        dock._del()

    dock.connect("unrealize", unrealize, notebooks)

    hbox = Gtk.HBox()

    # Buttons
    notebooks["buttons"].set_border_width(4)
    hbox.pack_start(notebooks["buttons"], False, True, 0)

    # The message area
    # TODO: If you try to fix this first read issue #958 and 1018
    align = createAlignment(0, 0, 0, 0)
    # sw = Gtk.ScrolledWindow()
    # port = Gtk.Viewport()
    # port.add(notebooks["messageArea"])
    # sw.add(port)
    # align.add(sw)
    align.add(notebooks["messageArea"])
    hbox.pack_start(align, True, True, 0)

    def ma_switch_page(notebook, gpointer, page_num):
        notebook.props.visible = notebook.get_nth_page(page_num).\
            get_child().props.visible

    notebooks["messageArea"].connect("switch-page", ma_switch_page)
    centerVBox.pack_start(hbox, False, True, 0)

    mainvbox.pack_start(centerVBox, True, True, 0)
    centerVBox.show_all()
    mainvbox.show()

    # Connecting headbook to other notebooks

    def hb_switch_page(notebook, gpointer, page_num):
        for notebook in notebooks.values():
            notebook.set_current_page(page_num)

#        log.debug("HB_switch ficsgame no. %s , %s " % (key2gmwidg[getheadbook().\
#           get_nth_page(page_num)].gamemodel.ficsgame.gameno,str(page_num)))
        gmwidg = key2gmwidg[getheadbook().get_nth_page(page_num)]
        if isinstance(gmwidg.gamemodel, ICGameModel):
            primary = "primary " + str(gmwidg.gamemodel.ficsgame.gameno)
            gmwidg.gamemodel.connection.client.run_command(primary)

    headbook.connect("switch-page", hb_switch_page)

    if hasattr(headbook, "set_tab_reorderable"):

        def page_reordered(widget, child, new_num, headbook):
            old_num = notebooks["board"].page_num(key2gmwidg[child].boardvbox)
            if old_num == -1:
                log.error('Games and labels are out of sync!')
            else:
                for notebook in notebooks.values():
                    notebook.reorder_child(
                        notebook.get_nth_page(old_num), new_num)

        headbook.connect("page-reordered", page_reordered, headbook)


def attachGameWidget(gmwidg):
    log.debug("attachGameWidget: %s" % gmwidg)
    _ensureReadForGameWidgets()
    headbook = getheadbook()

    key2gmwidg[gmwidg.notebookKey] = gmwidg

    headbook.append_page(gmwidg.notebookKey, gmwidg.tabcontent)
    gmwidg.notebookKey.show_all()
    # headbook.set_tab_label_packing(gmwidg.notebookKey, True, True, Gtk.PACK_START)
    if hasattr(headbook, "set_tab_reorderable"):
        headbook.set_tab_reorderable(gmwidg.notebookKey, True)

    def callback(notebook, gpointer, page_num, gmwidg):
        if notebook.get_nth_page(page_num) == gmwidg.notebookKey:
            gmwidg.infront()
            if gmwidg.gamemodel.players and gmwidg.gamemodel.isObservationGame():
                gmwidg.light_on_off(False)
                text = gmwidg.game_info_label.get_text()
                gmwidg.game_info_label.set_markup(
                    '<span color="black" weight="bold">%s</span>' % text)

    key2cid[gmwidg.notebookKey] = headbook.connect_after("switch-page", callback, gmwidg)
    gmwidg.infront()

    align = createAlignment(0, 0, 0, 0)
    align.show()
    align.add(gmwidg.infobar)
    notebooks["messageArea"].append_page(align, None)
    notebooks["board"].append_page(gmwidg.boardvbox, None)
    gmwidg.boardvbox.show_all()
    for panel, instance in zip(sidePanels, gmwidg.panels):
        notebooks[panel.__name__].append_page(instance, None)
        instance.show_all()
    notebooks["buttons"].append_page(gmwidg.stat_hbox, None)
    gmwidg.stat_hbox.show_all()

    # We should always show tabs if more than one exists
    if headbook.get_n_pages() == 2:
        show_tabs(True)

    headbook.set_current_page(-1)

    if headbook.get_n_pages() == 1 and not widgets["show_sidepanels"].get_active():
        zoomToBoard(True)


def cur_gmwidg():
    headbook = getheadbook()
    if headbook is None:
        return None
    notebookKey = headbook.get_nth_page(headbook.get_current_page())
    return key2gmwidg[notebookKey]


def customGetTabLabelText(child):
    gmwidg = key2gmwidg[child]
    return gmwidg.display_text


def getheadbook():
    if len(widgets["mainvbox"].get_children()) == 2:
        # If the headbook hasn't been added yet
        return None
    headbook = widgets["mainvbox"].get_children()[1].get_child()
    # to help StoryText create widget description
    headbook.get_tab_label_text = customGetTabLabelText
    return headbook


def zoomToBoard(view_zoomed):
    if len(widgets["mainvbox"].get_children()) == 2:
        # If the headbook hasn't been added yet
        return None
    if not notebooks["board"].get_parent():
        return
    if view_zoomed:
        notebooks["board"].get_parent().get_parent().zoomUp()
    else:
        notebooks["board"].get_parent().get_parent().zoomDown()


def show_tabs(show):
    if show:
        widgets["mainvbox"].get_children()[1].show_all()
    else:
        widgets["mainvbox"].get_children()[1].hide()


def tabsCallback(none):
    head = getheadbook()
    if not head:
        return
    if head.get_n_pages() == 1:
        show_tabs(not conf.get("hideTabs", False))


conf.notify_add("hideTabs", tabsCallback)

# ###############################################################################
# Handling of the special sidepanels-design-gamewidget used in preferences     #
# ###############################################################################

designGW = None


def showDesignGW():
    global designGW
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

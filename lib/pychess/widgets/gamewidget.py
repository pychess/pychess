""" This module handles the tabbed layout in PyChess """

import sys
from collections import defaultdict

from gi.repository import Gtk, GObject

import pychess
from .BoardControl import BoardControl
from .ChessClock import ChessClock
from .MenuItemsDict import MenuItemsDict
from pychess.System import conf

from pychess.System.Log import log
from pychess.Utils.IconLoader import get_pixbuf
from pychess.Utils.const import REMOTE, UNFINISHED_STATES, PAUSED, RUNNING, LOCAL, \
    WHITE, BLACK, ACTION_MENU_ITEMS, DRAW, UNDOABLE_STATES, HINT, SPY, WHITEWON, \
    MENU_ITEMS, BLACKWON, DROP, FAN_PIECES, TOOL_CHESSDB, TOOL_SCOUTFISH
from pychess.Utils.GameModel import GameModel
from pychess.Utils.Move import listToMoves
from pychess.Utils.lutils import lmove
from pychess.Utils.lutils.lmove import ParsingError
from pychess.Utils.logic import playerHasMatingMaterial, isClaimableDraw
from pychess.ic import get_infobarmessage_content, get_infobarmessage_content2
from pychess.ic.FICSObjects import get_player_tooltip_text
from pychess.ic.ICGameModel import ICGameModel
from pychess.widgets import createImage, createAlignment, gtk_close
from pychess.widgets.InfoBar import InfoBarNotebook, InfoBarMessage, InfoBarMessageButton
from pychess.perspectives import perspective_manager


light_on = get_pixbuf("glade/16x16/weather-clear.png")
light_off = get_pixbuf("glade/16x16/weather-clear-night.png")

widgets = None


def setWidgets(w):
    global widgets
    widgets = w
    pychess.widgets.main_window = widgets["main_window"]


def getWidgets():
    return widgets


class GameWidget(GObject.GObject):

    __gsignals__ = {
        'game_close_clicked': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'title_changed': (GObject.SignalFlags.RUN_FIRST, None, (str, )),
        'closed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, gamemodel, perspective):
        GObject.GObject.__init__(self)
        self.gamemodel = gamemodel
        self.perspective = perspective
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
            self.gamemodel.connect("message_received", self.message_received),
        ]
        self.players_changed(self.gamemodel)

        self.notify_cids = [conf.notify_add("showFICSgameno", self.on_show_fics_gameno), ]

        if self.gamemodel.display_text:
            if isinstance(self.gamemodel, ICGameModel) and conf.get("showFICSgameno"):
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

        if isinstance(self.gamemodel, ICGameModel):
            self.gamemodel.gmwidg_ready.set()

    def _del(self):
        if self.gamemodel.offline_lecture:
            self.gamemodel.lecture_exit_event.set()

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
        if isinstance(self.gamemodel, ICGameModel) and conf.get("showFICSgameno"):
            self.game_info_label.set_text(" [%s]" % self.gamemodel.ficsgame.gameno)
        else:
            self.game_info_label.set_text("")

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
        getWidgets()['main_window'].set_title(self.display_text + (" - " if self.display_text != "" else "") + "PyChess")

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

        self.on_shapes_changed(self.board)

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
            if gamemodel.connection is not None and not gamemodel.connection.ICC:
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

        # print(gamemodel.waitingplayer, gamemodel.waitingplayer.__type__)
        if not gamemodel.isPlayingICSGame():
            self.clearMessages()

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
            ply, movstrs, score, depth, nps = analysis[0]
            board = analyzer.board
            try:
                moves = listToMoves(board, movstrs, validate=True)
            except ParsingError as e:
                # ParsingErrors may happen when parsing "old" lines from
                # analyzing engines, which haven't yet noticed their new tasks
                log.debug("GameWidget._on_analyze(): Ignored (%s) from analyzer: ParsingError%s" %
                          (' '.join(movstrs), e))
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

    def show_arrow(self, analyzer, analyzer_type):
        self.menuitems[analyzer_type + "_mode"].active = True
        self._on_analyze(analyzer, analyzer.getAnalysis(), analyzer_type)
        return False

    def hide_arrow(self, analyzer, analyzer_type):
        self.menuitems[analyzer_type + "_mode"].active = False
        self._set_arrow(analyzer_type, None)
        return False

    def player_display_text(self, color, with_elo):
        text = ""
        if isinstance(self.gamemodel, ICGameModel):
            if self.gamemodel.ficsplayers:
                text = self.gamemodel.ficsplayers[color].name
                if (self.gamemodel.connection.username ==
                    self.gamemodel.ficsplayers[color].name) and \
                        self.gamemodel.ficsplayers[color].isGuest():
                    text += " (Player)"
        else:
            if self.gamemodel.players:
                text = repr(self.gamemodel.players[color])
        if with_elo:
            elo = self.gamemodel.tags.get("WhiteElo" if color == WHITE else "BlackElo")
            if elo:
                text += " (%s)" % str(elo)
        return text

    @property
    def display_text(self):
        if not self.gamemodel.players:
            return ""
        '''This will give you the name of the game.'''
        vs = " - "
        t = vs.join((self.player_display_text(WHITE, True),
                     self.player_display_text(BLACK, True)))
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

        if self.gamemodel is None:
            return
        name = self.player_display_text(color, False)
        self.gamemodel.tags["White" if color == WHITE else "Black"] = name
        self.player_name_labels[color].set_text(name)
        if isinstance(self.gamemodel, ICGameModel) and \
                player.__type__ == REMOTE:
            self.player_name_labels[color].set_tooltip_text(
                get_player_tooltip_text(self.gamemodel.ficsplayers[color],
                                        show_status=False))

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
        text_hbox.pack_start(Gtk.Label(label=" - "), False, True, 0)
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

        if self.gamemodel.offline_lecture:
            preview = True
        else:
            preview = False

        board = BoardControl(gamemodel, actionMenuDic, game_preview=preview)
        boardvbox.pack_start(board, True, True, 0)
        return boardvbox, board, infobar, cclock

    def initButtons(self, board):
        align = createAlignment(4, 0, 4, 0)
        toolbar = Gtk.Toolbar()

        firstButton = Gtk.ToolButton(stock_id=Gtk.STOCK_MEDIA_PREVIOUS)
        firstButton.set_tooltip_text(_("Jump to initial position"))
        toolbar.insert(firstButton, -1)

        prevButton = Gtk.ToolButton(stock_id=Gtk.STOCK_MEDIA_REWIND)
        prevButton.set_tooltip_text(_("Step back one move"))
        toolbar.insert(prevButton, -1)

        mainButton = Gtk.ToolButton(stock_id=Gtk.STOCK_GOTO_FIRST)
        mainButton.set_tooltip_text(_("Go back to the main line"))
        toolbar.insert(mainButton, -1)

        upButton = Gtk.ToolButton(stock_id=Gtk.STOCK_GOTO_TOP)
        upButton.set_tooltip_text(_("Go back to the parent line"))
        toolbar.insert(upButton, -1)

        nextButton = Gtk.ToolButton(stock_id=Gtk.STOCK_MEDIA_FORWARD)
        nextButton.set_tooltip_text(_("Step forward one move"))
        toolbar.insert(nextButton, -1)

        lastButton = Gtk.ToolButton(stock_id=Gtk.STOCK_MEDIA_NEXT)
        lastButton.set_tooltip_text(_("Jump to latest position"))
        toolbar.insert(lastButton, -1)

        filterButton = Gtk.ToolButton(stock_id=Gtk.STOCK_FIND)
        filterButton.set_tooltip_text(_("Find postion in current database"))
        toolbar.insert(filterButton, -1)

        self.saveButton = Gtk.ToolButton(stock_id=Gtk.STOCK_SAVE)
        self.saveButton.set_tooltip_text(_("Save arrows/circles"))
        toolbar.insert(self.saveButton, -1)

        def on_clicked(button, func):
            # Prevent moving in game while lesson not finished
            if self.gamemodel.lesson_game and not self.gamemodel.solved:
                return
            else:
                func()

        self.cids[firstButton] = firstButton.connect("clicked", on_clicked, self.board.view.showFirst)
        self.cids[prevButton] = prevButton.connect("clicked", on_clicked, self.board.view.showPrev)
        self.cids[mainButton] = mainButton.connect("clicked", on_clicked, self.board.view.backToMainLine)
        self.cids[upButton] = upButton.connect("clicked", on_clicked, self.board.view.backToParentLine)
        self.cids[nextButton] = nextButton.connect("clicked", on_clicked, self.board.view.showNext)
        self.cids[lastButton] = lastButton.connect("clicked", on_clicked, self.board.view.showLast)
        self.cids[filterButton] = filterButton.connect("clicked", on_clicked, self.find_in_database)
        self.cids[self.saveButton] = self.saveButton.connect("clicked", on_clicked, self.save_shapes_to_pgn)

        self.on_shapes_changed(self.board)
        self.board.connect("shapes_changed", self.on_shapes_changed)

        tool_box = Gtk.Box()
        tool_box.pack_start(toolbar, True, True, 0)

        align.add(tool_box)
        return align

    def on_shapes_changed(self, boardcontrol):
        self.saveButton.set_sensitive(boardcontrol.view.has_unsaved_shapes)

    def find_in_database(self):
        persp = perspective_manager.get_perspective("database")
        if persp.chessfile is None:
            dialogue = Gtk.MessageDialog(pychess.widgets.mainwindow(),
                                         type=Gtk.MessageType.ERROR,
                                         buttons=Gtk.ButtonsType.OK,
                                         message_format=_("No database is currently opened."))
            dialogue.run()
            dialogue.destroy()
            return

        view = self.board.view
        shown_board = self.gamemodel.getBoardAtPly(view.shown, view.shown_variation_idx)
        fen = shown_board.asFen()

        tool, found = persp.chessfile.has_position(fen)
        if not found:
            dialogue = Gtk.MessageDialog(pychess.widgets.mainwindow(),
                                         type=Gtk.MessageType.WARNING,
                                         buttons=Gtk.ButtonsType.OK,
                                         message_format=_("The position does not exist in the database."))
            dialogue.run()
            dialogue.destroy()
        else:
            if tool == TOOL_CHESSDB:
                persp.chessfile.set_fen_filter(fen)
            elif tool == TOOL_SCOUTFISH:
                dialogue = Gtk.MessageDialog(pychess.widgets.mainwindow(),
                                             type=Gtk.MessageType.QUESTION,
                                             buttons=Gtk.ButtonsType.YES_NO,
                                             message_format=_("An approximate position has been found. Do you want to display it ?"))
                response = dialogue.run()
                dialogue.destroy()
                if response != Gtk.ResponseType.YES:
                    return

                persp.chessfile.set_scout_filter({'sub-fen': fen})
            else:
                raise RuntimeError('Internal error')
            persp.gamelist.ply = view.shown
            persp.gamelist.load_games()
            perspective_manager.activate_perspective("database")

    def save_shapes_to_pgn(self):
        view = self.board.view
        shown_board = self.gamemodel.getBoardAtPly(view.shown, view.shown_variation_idx)

        for child in shown_board.board.children:
            if isinstance(child, str):
                if child.lstrip().startswith("[%csl "):
                    shown_board.board.children.remove(child)
                    self.gamemodel.needsSave = True
                elif child.lstrip().startswith("[%cal "):
                    shown_board.board.children.remove(child)
                    self.gamemodel.needsSave = True

        if view.circles:
            csl = []
            for circle in view.circles:
                csl.append("%s%s" % (circle.color, repr(circle)))
            shown_board.board.children = ["[%%csl %s]" % ",".join(csl)] + shown_board.board.children
            self.gamemodel.needsSave = True

        if view.arrows:
            cal = []
            for arrow in view.arrows:
                cal.append("%s%s%s" % (arrow[0].color, repr(arrow[0]), repr(arrow[1])))
            shown_board.board.children = ["[%%cal %s]" % ",".join(cal)] + shown_board.board.children
            self.gamemodel.needsSave = True

        view.saved_arrows = set()
        view.saved_arrows |= view.arrows

        view.saved_circles = set()
        view.saved_circles |= view.circles

        self.on_shapes_changed(self.board)

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
        self.perspective.getheadbook().set_current_page(self.getPageNumber())

    def isInFront(self):
        if not self.perspective.getheadbook():
            return False
        return self.perspective.getheadbook().get_current_page() == self.getPageNumber()

    def getPageNumber(self):
        return self.perspective.getheadbook().page_num(self.notebookKey)

    def infobar_hidden(self, infobar):
        if self == self.perspective.cur_gmwidg():
            self.perspective.notebooks["messageArea"].hide()

    def showMessage(self, message):
        self.infobar.push_message(message)
        if self == self.perspective.cur_gmwidg():
            self.perspective.notebooks["messageArea"].show()

    def replaceMessages(self, message):
        """ Replace all messages with message """
        if not self.closed:
            self.infobar.clear_messages()
            self.showMessage(message)

    def clearMessages(self):
        self.infobar.clear_messages()
        if self == self.perspective.cur_gmwidg():
            self.perspective.notebooks["messageArea"].hide()


# ###############################################################################
# Handling of the special sidepanels-design-gamewidget used in preferences     #
# ###############################################################################

designGW = None


def showDesignGW():
    global designGW
    perspective = perspective_manager.get_perspective("games")
    designGW = GameWidget(GameModel(), perspective)
    if isDesignGWShown():
        return
    getWidgets()["show_sidepanels"].set_active(True)
    getWidgets()["show_sidepanels"].set_sensitive(False)
    perspective.attachGameWidget(designGW)


def hideDesignGW():
    if isDesignGWShown():
        perspective = perspective_manager.get_perspective("games")
        perspective.delGameWidget(designGW)
    getWidgets()["show_sidepanels"].set_sensitive(True)


def isDesignGWShown():
    perspective = perspective_manager.get_perspective("games")
    return designGW in perspective.key2gmwidg.values()

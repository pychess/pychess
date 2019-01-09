""" This module intends to work as glue between the gamemodel and the gamewidget
    taking care of stuff that is neither very offscreen nor very onscreen
    like bringing up dialogs and """

import math
from collections import defaultdict

from gi.repository import Gtk

from pychess.compat import create_task
from pychess.ic.FICSObjects import make_sensitive_if_available, make_sensitive_if_playing
from pychess.ic.ICGameModel import ICGameModel
from pychess.Utils.Offer import Offer
from pychess.Utils.const import WAITING_TO_START, WHITE, BLACK, WHITEWON, \
    BLACKWON, WON_ADJUDICATION, TAKEBACK_OFFER, LOCAL, UNDOABLE_STATES, WHITE_ENGINE_DIED, \
    UNDOABLE_REASONS, BLACK_ENGINE_DIED, HINT, SPY, RUNNING, ABORT_OFFER, ADJOURN_OFFER, \
    DRAW_OFFER, PAUSE_OFFER, RESUME_OFFER, HURRY_ACTION, FLAG_CALL
from pychess.Utils.repr import reprResult_long, reprReason_long
from pychess.Utils.LearnModel import LearnModel
from pychess.System import conf
from pychess.System.Log import log
from pychess.widgets import preferencesDialog
from pychess.widgets.InfoBar import InfoBarMessage, InfoBarMessageButton
from pychess.widgets import InfoBar, mainwindow
from pychess.widgets.gamewidget import getWidgets
from pychess.perspectives import perspective_manager


class GameNanny:
    def __init__(self):
        self.offer_cids = defaultdict(dict)
        self.gmwidg_cids = defaultdict(list)
        self.model_cids = defaultdict(list)

    def nurseGame(self, gmwidg, gamemodel):
        """ Call this function when gmwidget is just created """
        log.debug("nurseGame: %s %s" % (gmwidg, gamemodel))
        self.gmwidg_cids[gmwidg] = [
            gmwidg.connect("closed", self.on_gmwidg_closed),
            gmwidg.connect("title_changed", self.on_gmwidg_title_changed),
        ]
        if gamemodel.status == WAITING_TO_START:
            self.model_cids[gamemodel].append(gamemodel.connect("game_started", self.on_game_started, gmwidg))
        else:
            self.on_game_started(gamemodel, gmwidg)

        self.model_cids[gamemodel].append(gamemodel.connect("game_ended", self.game_ended, gmwidg))
        self.model_cids[gamemodel].append(gamemodel.connect("game_terminated", self.on_game_terminated, gmwidg))

        if isinstance(gamemodel, ICGameModel):
            gmwidg.cids[gamemodel.connection] = gamemodel.connection.connect("disconnected", self.on_disconnected, gmwidg)

    def on_game_terminated(self, gamemodel, gmwidg):
        for player in self.offer_cids[gamemodel]:
            player.disconnect(self.offer_cids[gamemodel][player])
        for cid in self.model_cids[gamemodel]:
            gamemodel.disconnect(cid)
        for cid in self.gmwidg_cids[gmwidg]:
            gmwidg.disconnect(cid)
        del self.offer_cids[gamemodel]
        del self.gmwidg_cids[gmwidg]
        del self.model_cids[gamemodel]

    def on_disconnected(self, fics_connection, gamewidget):
        def disable_buttons():
            for button in gamewidget.game_ended_message.buttons:
                button.set_property("sensitive", False)
                button.set_property("tooltip-text", "")

        if gamewidget.game_ended_message:
            disable_buttons

    # ===============================================================================
    # Gamewidget signals
    # ===============================================================================

    def on_gmwidg_closed(self, gmwidg):
        perspective = perspective_manager.get_perspective("games")
        if len(perspective.key2gmwidg) == 1:
            getWidgets()['main_window'].set_title('%s - PyChess' % _('Welcome'))
        return False

    def on_gmwidg_title_changed(self, gmwidg, new_title):
        # log.debug("gamenanny.on_gmwidg_title_changed: starting %s" % repr(gmwidg))
        if gmwidg.isInFront():
            getWidgets()['main_window'].set_title('%s - PyChess' % new_title)
        # log.debug("gamenanny.on_gmwidg_title_changed: returning")
        return False

    # ===============================================================================
    # Gamemodel signals
    # ===============================================================================

    def game_ended(self, gamemodel, reason, gmwidg):
        log.debug("gamenanny.game_ended: reason=%s gmwidg=%s\ngamemodel=%s" %
                  (reason, gmwidg, gamemodel))
        nameDic = {"white": gamemodel.players[WHITE],
                   "black": gamemodel.players[BLACK],
                   "mover": gamemodel.curplayer}
        if gamemodel.status == WHITEWON:
            nameDic["winner"] = gamemodel.players[WHITE]
            nameDic["loser"] = gamemodel.players[BLACK]
        elif gamemodel.status == BLACKWON:
            nameDic["winner"] = gamemodel.players[BLACK]
            nameDic["loser"] = gamemodel.players[WHITE]
        msg_one = reprResult_long[gamemodel.status] % nameDic
        msg_two = reprReason_long[reason] % nameDic
        if gamemodel.reason == WON_ADJUDICATION:
            color = BLACK if gamemodel.status == WHITEWON else WHITE
            invalid_move = gamemodel.players[color].invalid_move
            if invalid_move:
                msg_two += _(" invalid engine move: %s" % invalid_move)

        content = InfoBar.get_message_content(msg_one, msg_two, Gtk.STOCK_DIALOG_INFO)
        message = InfoBarMessage(Gtk.MessageType.INFO, content, None)

        callback = None
        if isinstance(gamemodel, ICGameModel):
            if gamemodel.hasLocalPlayer() and not gamemodel.examined:

                def status_changed(player, prop, message):
                    make_sensitive_if_available(message.buttons[0], player)
                    make_sensitive_if_playing(message.buttons[1], player)

                def callback(infobar, response, message, gamemodel=gamemodel):
                    if response == 0:
                        gamemodel.remote_player.offerRematch()
                    elif response == 1:
                        gamemodel.remote_player.observe()
                    return False
                gmwidg.cids[gamemodel.remote_ficsplayer] = \
                    gamemodel.remote_ficsplayer.connect("notify::status", status_changed, message)
                message.add_button(InfoBarMessageButton(_("Offer Rematch"), 0))
                message.add_button(InfoBarMessageButton(
                    _("Observe %s" % gamemodel.remote_ficsplayer.name), 1))
                status_changed(gamemodel.remote_ficsplayer, None, message)

            else:

                def status_changed(player, prop, button):
                    make_sensitive_if_playing(button, player)

                def callback(infobar, response, message, gamemodel=gamemodel):
                    if response in (0, 1):
                        gamemodel.players[response].observe()
                    return False

                for i, player in enumerate(gamemodel.ficsplayers):
                    button = InfoBarMessageButton(_("Observe %s" % player.name), i)
                    message.add_button(button)
                    gmwidg.cids[player] = player.connect("notify::status", status_changed, button)
                    status_changed(player, None, button)

        elif gamemodel.hasLocalPlayer() and not isinstance(gamemodel, LearnModel):

            def callback(infobar, response, message, gamemodel=gamemodel):
                if response == 1:
                    # newGameDialog uses perspectives.games uses gamenanny uses newGameDialog...
                    from pychess.widgets.newGameDialog import createRematch
                    createRematch(gamemodel)
                elif response == 2:
                    if gamemodel.ply > 1:
                        offer = Offer(TAKEBACK_OFFER, 2)
                    else:
                        offer = Offer(TAKEBACK_OFFER, 1)
                    if gamemodel.players[0].__type__ == LOCAL:
                        gamemodel.players[0].emit("offer", offer)
                    else:
                        gamemodel.players[1].emit("offer", offer)
                return False

            if not gamemodel.isLoadedGame():
                message.add_button(InfoBarMessageButton(_("Play Rematch"), 1))
            if gamemodel.status in UNDOABLE_STATES and gamemodel.reason in UNDOABLE_REASONS:
                if gamemodel.ply == 1:
                    message.add_button(InfoBarMessageButton(_("Undo one move"), 2))
                elif gamemodel.ply > 1:
                    message.add_button(InfoBarMessageButton(
                        _("Undo two moves"), 2))

        message.callback = callback
        gmwidg.game_ended_message = message

        perspective = perspective_manager.get_perspective("games")
        if len(perspective.key2gmwidg) > 0:
            gmwidg.replaceMessages(message)

        if reason == WHITE_ENGINE_DIED:
            self.engineDead(gamemodel.players[0], gmwidg)
        elif reason == BLACK_ENGINE_DIED:
            self.engineDead(gamemodel.players[1], gmwidg)

        if (isinstance(gamemodel, ICGameModel) and not gamemodel.isObservationGame()) or \
                gamemodel.isEngine2EngineGame() or \
                (isinstance(gamemodel, LearnModel) and not gamemodel.failed_playing_best):
            create_task(gamemodel.restart_analyzer(HINT))
            create_task(gamemodel.restart_analyzer(SPY))
            if not conf.get("hint_mode"):
                gamemodel.pause_analyzer(HINT)
            if not conf.get("spy_mode"):
                gamemodel.pause_analyzer(SPY)

        return False

    def on_game_started(self, gamemodel, gmwidg):
        # offline lectures can reuse same gamemodel/gamewidget
        # to show several examples inside the same lecture
        if gamemodel.offline_lecture:
            gmwidg.clearMessages()

        # Rotate to human player
        boardview = gmwidg.board.view
        if gamemodel.players[1].__type__ == LOCAL:
            if gamemodel.players[0].__type__ != LOCAL:
                boardview.rotation = math.pi

        if isinstance(gamemodel, LearnModel):
            if gamemodel.orientation == BLACK:
                boardview.rotation = math.pi
            else:
                boardview.rotation = 0

        # Play set-up sound
        preferencesDialog.SoundTab.playAction("gameIsSetup")

        # Connect player offers to infobar
        for player in gamemodel.players:
            if player.__type__ == LOCAL:
                self.offer_cids[gamemodel][player] = player.connect(
                    "offer", self.offer_callback, gamemodel, gmwidg)

        # Start analyzers if any
        if not gamemodel.isEngine2EngineGame():
            create_task(gamemodel.start_analyzer(HINT))
            create_task(gamemodel.start_analyzer(SPY))
            if not conf.get("hint_mode"):
                gamemodel.pause_analyzer(HINT)
            if not conf.get("spy_mode"):
                gamemodel.pause_analyzer(SPY)
        return False

    # ===============================================================================
    # Player signals
    # ===============================================================================

    def offer_callback(self, player, offer, gamemodel, gmwidg):
        if gamemodel.status != RUNNING:
            # If the offer has already been handled by Gamemodel and the game was
            # drawn, we need to do nothing
            return

        message = ""
        if offer.type == ABORT_OFFER:
            message = _("You sent an abort offer")
        elif offer.type == ADJOURN_OFFER:
            message = _("You sent an adjournment offer")
        elif offer.type == DRAW_OFFER:
            message = _("You sent a draw offer")
        elif offer.type == PAUSE_OFFER:
            message = _("You sent a pause offer")
        elif offer.type == RESUME_OFFER:
            message = _("You sent a resume offer")
        elif offer.type == TAKEBACK_OFFER:
            message = _("You sent an undo offer")
        elif offer.type == HURRY_ACTION:
            message = _("You asked your opponent to move")
        elif offer.type == FLAG_CALL:
            message = _("You sent flag call")
        else:
            return

        def response_cb(infobar, response, message):
            message.dismiss()
            return False
        content = InfoBar.get_message_content("", message, Gtk.STOCK_DIALOG_INFO)
        message = InfoBarMessage(Gtk.MessageType.INFO, content, response_cb)
        gmwidg.replaceMessages(message)

        return False

    # ===============================================================================
    # Subfunctions
    # ===============================================================================

    def engineDead(self, engine, gmwidg):
        gmwidg.bringToFront()
        dialog = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.OK)
        dialog.set_markup(_("<big><b>Engine, %s, has died</b></big>") % repr(engine))
        dialog.format_secondary_text(_(
            "PyChess has lost connection to the engine, probably because it has died.\n\n \
            You can try to start a new game with the engine, or try to play against another one."))
        dialog.connect("response", lambda dialog, r: dialog.hide())
        dialog.show_all()


game_nanny = GameNanny()

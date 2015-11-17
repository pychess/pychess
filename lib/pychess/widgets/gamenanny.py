""" This module intends to work as glue between the gamemodel and the gamewidget
    taking care of stuff that is neither very offscreen nor very onscreen
    like bringing up dialogs and """
from __future__ import absolute_import

import math
from gi.repository import Gtk

from pychess.compat import unicode
from pychess.ic.FICSObjects import make_sensitive_if_available, make_sensitive_if_playing
from pychess.ic.ICGameModel import ICGameModel
from pychess.Utils.Offer import Offer
from pychess.Utils.const import *
from pychess.Utils.repr import reprResult_long, reprReason_long
from pychess.System import conf
from pychess.System.idle_add import idle_add
from pychess.System.Log import log
from pychess.widgets import preferencesDialog
from pychess.widgets.InfoBar import InfoBarMessage, InfoBarMessageButton
from pychess.widgets import InfoBar

from .gamewidget import getWidgets, key2gmwidg, isDesignGWShown

def nurseGame (gmwidg, gamemodel):
    """ Call this function when gmwidget is just created """
    log.debug("nurseGame: %s %s" % (gmwidg, gamemodel))
    gmwidg.connect("infront", on_gmwidg_infront)
    gmwidg.connect("closed", on_gmwidg_closed)
    gmwidg.connect("title_changed", on_gmwidg_title_changed)
    
    # Because of the async loading of games, the game might already be started,
    # when nurseGame is called.
    # Thus we support both cases.
    if gamemodel.status == WAITING_TO_START:
        gamemodel.connect("game_started", on_game_started, gmwidg)
        gamemodel.connect("game_loaded", game_loaded, gmwidg)
    else:
        if gamemodel.uri:
            game_loaded(gamemodel, gamemodel.uri, gmwidg)
        on_game_started(gamemodel, gmwidg)
    
    gamemodel.connect("game_saved", game_saved, gmwidg)
    gamemodel.connect("game_ended", game_ended, gmwidg)
    gamemodel.connect("game_unended", game_unended, gmwidg)
    gamemodel.connect("game_resumed", game_unended, gmwidg)
    gamemodel.connect("game_changed", game_changed, gmwidg)
    gamemodel.connect("game_paused", game_paused, gmwidg)

    if isinstance(gamemodel, ICGameModel):
        gamemodel.connection.connect("disconnected", on_disconnected, gmwidg)

def on_disconnected (fics_connection, gamewidget):
    @idle_add
    def disable_buttons():
        for b in gamewidget.game_ended_message.buttons:
            b.set_property("sensitive", False)
            b.set_property("tooltip-text", "")
    if gamewidget.game_ended_message:
        disable_buttons()
#===============================================================================
# Gamewidget signals
#===============================================================================
@idle_add
def on_gmwidg_infront (gmwidg):
    for widget in MENU_ITEMS:
        if widget in gmwidg.menuitems:
            continue
        elif widget == 'show_sidepanels' and isDesignGWShown():
            getWidgets()[widget].set_property('sensitive', False)
        else:
            getWidgets()[widget].set_property('sensitive', True)
    
    # Change window title
    getWidgets()['window1'].set_title('%s - PyChess' % gmwidg.display_text)
    return False

@idle_add
def on_gmwidg_closed (gmwidg):
    if len(key2gmwidg) == 1:
        getWidgets()['window1'].set_title('%s - PyChess' % _('Welcome'))
    return False


@idle_add
def on_gmwidg_title_changed (gmwidg, new_title):
    #log.debug("gamenanny.on_gmwidg_title_changed: starting %s" % repr(gmwidg))
    if gmwidg.isInFront():
        getWidgets()['window1'].set_title('%s - PyChess' % new_title)
    #log.debug("gamenanny.on_gmwidg_title_changed: returning")
    return False

#===============================================================================
# Gamemodel signals
#===============================================================================

@idle_add
def game_ended (gamemodel, reason, gmwidg):
    log.debug("gamenanny.game_ended: reason=%s gmwidg=%s\ngamemodel=%s" % \
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
    m1 = reprResult_long[gamemodel.status] % nameDic
    m2 = reprReason_long[reason] % nameDic
    if gamemodel.reason == WON_ADJUDICATION:
        color = BLACK if gamemodel.status == WHITEWON else WHITE
        invalid_move = gamemodel.players[color].invalid_move
        if invalid_move:
            m2 += _(" invalid engine move: %s" % invalid_move)

    content = InfoBar.get_message_content(m1, m2, Gtk.STOCK_DIALOG_INFO)
    message = InfoBarMessage(Gtk.MessageType.INFO, content, None)

    callback = None
    if isinstance(gamemodel, ICGameModel):
        if gamemodel.hasLocalPlayer():
            def status_changed (player, prop, message):
                make_sensitive_if_available(message.buttons[0], player)
                make_sensitive_if_playing(message.buttons[1], player)
            def callback (infobar, response, message):
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
            def status_changed (player, prop, button):
                make_sensitive_if_playing(button, player)
            def callback (infobar, response, message):
                if response in (0, 1):
                    gamemodel.players[response].observe()
                return False
            for i, p in enumerate(gamemodel.ficsplayers):
                b = InfoBarMessageButton(_("Observe %s" % p.name), i)
                message.add_button(b)
                gmwidg.cids[p] = p.connect("notify::status", status_changed, b)
                status_changed(p, None, b)

    elif gamemodel.hasLocalPlayer():
        def callback (infobar, response, message):
            if response == 1:
                # newGameDialog uses ionest uses gamenanny uses newGameDialog...
                from pychess.widgets.newGameDialog import createRematch
                createRematch(gamemodel)
            elif response == 2:
                if gamemodel.ply > 1:
                    offer = Offer(TAKEBACK_OFFER, gamemodel.ply-2)
                else:
                    offer = Offer(TAKEBACK_OFFER, gamemodel.ply-1)
                if gamemodel.players[0].__type__ == LOCAL:
                    gamemodel.players[0].emit("offer", offer)
                else: gamemodel.players[1].emit("offer", offer)
            return False
        if not gamemodel.isLoadedGame():
            message.add_button(InfoBarMessageButton(_("Play Rematch"), 1))
        if gamemodel.status in UNDOABLE_STATES and gamemodel.reason in UNDOABLE_REASONS:
            if gamemodel.ply == 1:
                message.add_button(InfoBarMessageButton(_("Undo one move"), 2))
            elif gamemodel.ply > 1:
                message.add_button(InfoBarMessageButton(_("Undo two moves"), 2))

    message.callback = callback
    gmwidg.game_ended_message = message

    if len(key2gmwidg) > 0:
        gmwidg.replaceMessages(message)
        gmwidg.status("%s %s." % (m1,m2[0].lower()+m2[1:]))
    
    if reason == WHITE_ENGINE_DIED:
        engineDead(gamemodel.players[0], gmwidg)
    elif reason == BLACK_ENGINE_DIED:
        engineDead(gamemodel.players[1], gmwidg)

    if (isinstance(gamemodel, ICGameModel) and not gamemodel.isObservationGame()) or \
            gamemodel.isEngine2EngineGame():
        gamemodel.restart_analyzer(HINT)
        gamemodel.restart_analyzer(SPY)
        if not conf.get("hint_mode", False):
            gamemodel.pause_analyzer(HINT)
        if not conf.get("spy_mode", False):
            gamemodel.pause_analyzer(SPY)
    
    return False

def _set_statusbar (gamewidget, message):
    assert isinstance(message, str) or isinstance(message, unicode)
    gamewidget.status(message)
    
def game_paused (gamemodel, gmwidg):
    s = _("The game is paused")
    _set_statusbar(gmwidg, s)
    return False
    
def game_changed (gamemodel, ply, gmwidg):
    _set_statusbar(gmwidg, "")
    return False

@idle_add
def game_unended (gamemodel, gmwidg):
    log.debug("gamenanny.game_unended: %s" % gamemodel.boards[-1])
    gmwidg.clearMessages()
    _set_statusbar(gmwidg, "")
    return False

# Connect game_loaded, game_saved and game_ended to statusbar
def game_loaded (gamemodel, uri, gmwidg):
    if type(uri) in (str, unicode):
        s = "%s: %s" % (_("Loaded game"), str(uri))
    else: s = _("Loaded game")
    
    _set_statusbar(gmwidg, s)
    return False

def game_saved (gamemodel, uri, gmwidg):
    _set_statusbar(gmwidg, "%s: %s" % (_("Saved game"), str(uri)))
    return False

def analyzer_added (gamemodel, analyzer, analyzer_type, gmwidg):
    s = _("Analyzer started") + ": " + analyzer.name
    _set_statusbar(gmwidg, s)
    return False

def on_game_started (gamemodel, gmwidg):
    on_gmwidg_infront(gmwidg)  # setup menu items sensitivity

    # Rotate to human player
    boardview = gmwidg.board.view
    if gamemodel.players[1].__type__ == LOCAL:
        if gamemodel.players[0].__type__ != LOCAL:
            boardview.rotation = math.pi
        elif conf.get("autoRotate", True) and \
                gamemodel.curplayer == gamemodel.players[1]:
            boardview.rotation = math.pi
    
    # Play set-up sound
    preferencesDialog.SoundTab.playAction("gameIsSetup")
    
    # Connect player offers to statusbar
    for player in gamemodel.players:
        if player.__type__ == LOCAL:
            player.connect("offer", offer_callback, gamemodel, gmwidg)
    
    # Start analyzers if any
    gamemodel.connect("analyzer_added", analyzer_added, gmwidg)
    if not (isinstance(gamemodel, ICGameModel) and \
            gamemodel.isObservationGame() is False) and \
       not gamemodel.isEngine2EngineGame():
        gamemodel.start_analyzer(HINT)
        gamemodel.start_analyzer(SPY)
        if not conf.get("hint_mode", False):
            gamemodel.pause_analyzer(HINT)
        if not conf.get("spy_mode", False):
            gamemodel.pause_analyzer(SPY)
    return False

#===============================================================================
# Player signals
#===============================================================================

def offer_callback (player, offer, gamemodel, gmwidg):
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
    
    _set_statusbar(gmwidg, message)
    return False

#===============================================================================
# Subfunctions
#===============================================================================

def engineDead (engine, gmwidg):
    gmwidg.bringToFront()
    d = Gtk.MessageDialog(type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK)
    d.set_markup(_("<big><b>Engine, %s, has died</b></big>") % repr(engine))
    d.format_secondary_text(_("PyChess has lost connection to the engine, probably because it has died.\n\nYou can try to start a new game with the engine, or try to play against another one."))
    d.connect("response", lambda d,r: d.hide())
    d.show_all()

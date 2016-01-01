# -*- coding: UTF-8 -*-

from gi.repository import Gtk
from gi.repository import Pango

import time

from pychess.System import uistuff
from pychess.System.idle_add import idle_add
from pychess.System.Log import log
from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import LOCAL, WHITE, BLACK
from pychess.widgets.ChatView import  ChatView
from pychess.ic.ICGameModel import ICGameModel
from pychess.ic.managers.ChatManager import ChatManager

__title__ = _("Chat")

__icon__ = addDataPrefix("glade/panel_chat.svg")

__desc__ = _("The chat panel lets you communicate with your opponent during the game, assuming he or she is interested")

class Sidepanel:


    def load (self, gmwidg):
        self.gamemodel = gmwidg.gamemodel
        self.gamemodel.connect("game_started", self.onGameStarted)
        self.chatView = ChatView(self.gamemodel)
        self.chatView.disable("Waiting for game to load")
        self.chatView.connect("messageTyped", self.onMessageSent)
        if isinstance(self.gamemodel, ICGameModel):
            self.gamemodel.connect("observers_received", self.chatView.update_observers)
            self.gamemodel.connect("message_received", self.onICMessageReieved)
        return self.chatView

    @idle_add
    def onGameStarted (self, gamemodel):
        if gamemodel.isObservationGame() or gamemodel.examined:
            # no local player but enable chat to send/receive whisper/kibitz
            pass
        elif gamemodel.players[0].__type__ == LOCAL:
            self.player = gamemodel.players[0]
            self.opplayer = gamemodel.players[1]
            if gamemodel.players[1].__type__ == LOCAL:
                log.warning("Chatpanel loaded with two local players")
        elif gamemodel.players[1].__type__ == LOCAL:
            self.player = gamemodel.players[1]
            self.opplayer = gamemodel.players[0]
        else:
            log.info("Chatpanel loaded with no local players")
            self.chatView.hide()

        if isinstance(gamemodel, ICGameModel):
            allob = 'allob ' + str(gamemodel.ficsgame.gameno)
            gamemodel.connection.client.run_command(allob)

        if hasattr(self, "player"):
            self.player.connect("messageReceived", self.onMessageReieved)

        self.chatView.enable()

    @idle_add
    def onMessageReieved (self, player, text):
        self.chatView.addMessage(repr(self.opplayer), text)

    def onICMessageReieved (self, icgamemodel, player, text):
        self.chatView.addMessage(player, text)
        # emit an allob <gameno> to FICS
        allob = 'allob ' + str(icgamemodel.ficsgame.gameno)
        icgamemodel.connection.client.run_command(allob)

    def onMessageSent (self, chatView, text):
        if hasattr(self, "player"):
            if text.startswith('# ') :
                text = text[2:]
                name = self.gamemodel.connection.cm.whisper(text)
            elif text.startswith('whisper '):
                text = text[8:]
                name = self.gamemodel.connection.cm.whisper(text)
            else :
                self.player.sendMessage(text)
                self.chatView.addMessage(repr(self.player), text)
        else:
            name = self.gamemodel.connection.cm.whisper(text)

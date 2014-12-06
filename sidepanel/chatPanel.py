# -*- coding: UTF-8 -*-

import gtk
import pango

import time

from pychess.System import uistuff
from pychess.System.idle_add import idle_add
from pychess.System.Log import log
from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import LOCAL, WHITE, BLACK
from pychess.widgets.ChatView import ChatView

__title__ = _("Chat")

__icon__ = addDataPrefix("glade/panel_chat.svg")

__desc__ = _("The chat panel lets you communicate with your opponent during the game, assuming he or she is interested")

class Sidepanel:
    def load (self, gmwidg):
        self.chatView = ChatView()
        self.chatView.disable("Waiting for game to load")
        self.chatView.connect("messageTyped", self.onMessageSent)
        self.gamemodel = gmwidg.gamemodel
        self.gamemodel.connect("game_started", self.onGameStarted)
        return self.chatView
    
    @idle_add
    def onGameStarted (self, gamemodel):
        if gamemodel.players[0].__type__ == LOCAL:
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
        
        if hasattr(self, "player"):
            self.player.connect("messageRecieved", self.onMessageReieved)
        
        self.chatView.enable()
    
    def onMessageReieved (self, player, text):
        self.chatView.addMessage(repr(self.opplayer), text)
    
    def onMessageSent (self, chatView, text):
        self.player.sendMessage(text)
        self.chatView.addMessage(repr(self.player), text)

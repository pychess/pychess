# -*- coding: UTF-8 -*-

from pychess.System.Log import log
from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import LOCAL
from pychess.widgets.ChatView import ChatView
from pychess.ic.ICGameModel import ICGameModel
from pychess.ic.icc import DG_PLAYERS_IN_MY_GAME

__title__ = _("Chat")

__icon__ = addDataPrefix("glade/panel_chat.svg")

__desc__ = _(
    "The chat panel lets you communicate with your opponent during the game, assuming he or she is interested")


class Sidepanel:
    def load(self, gmwidg):
        self.gamemodel = gmwidg.gamemodel
        self.player_cid = None
        self.model_cids = [
            self.gamemodel.connect("game_started", self.onGameStarted),
            self.gamemodel.connect_after("game_terminated", self.on_game_terminated),
        ]
        self.chatView = ChatView(self.gamemodel)
        self.chatView.disable("Waiting for game to load")
        self.chatview_cid = self.chatView.connect("messageTyped", self.onMessageSent)
        if isinstance(self.gamemodel, ICGameModel):
            self.model_cids.append(self.gamemodel.connect("observers_received",
                                   self.chatView.update_observers))
            self.model_cids.append(self.gamemodel.connect("message_received",
                                   self.onICMessageReieved))
        return self.chatView

    def on_game_terminated(self, model):
        self.chatView.disconnect(self.chatview_cid)
        if hasattr(self, "player") and hasattr(self, "player_cid") and not self.gamemodel.examined:
            self.player.disconnect(self.player_cid)
        for cid in self.model_cids:
            self.gamemodel.disconnect(cid)

    def onGameStarted(self, gamemodel):
        if gamemodel.examined:
            if gamemodel.players[0].name == gamemodel.connection.username:
                self.player = gamemodel.players[0]
                self.opplayer = gamemodel.players[1]
            else:
                self.player = gamemodel.players[1]
                self.opplayer = gamemodel.players[0]
        elif gamemodel.isObservationGame():
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
            if gamemodel.connection.ICC:
                gamemodel.connection.client.run_command("set-2 %s 1" % DG_PLAYERS_IN_MY_GAME)
            else:
                allob = 'allob ' + str(gamemodel.ficsgame.gameno)
                gamemodel.connection.client.run_command(allob)

        if hasattr(self, "player") and not gamemodel.examined and self.player_cid is None:
            self.player_cid = self.player.connect("messageReceived", self.onMessageRecieved)

        self.chatView.enable()

    def onMessageRecieved(self, player, text):
        sender = "pychessbot" if player.gamemodel.offline_lecture else repr(self.opplayer)
        self.chatView.addMessage(sender, text)

    def onICMessageReieved(self, icgamemodel, player, text):
        self.chatView.addMessage(player, text)
        # emit an allob <gameno> to FICS
        if not icgamemodel.connection.ICC:
            allob = 'allob ' + str(icgamemodel.ficsgame.gameno)
            icgamemodel.connection.client.run_command(allob)

    def onMessageSent(self, chatView, text):
        if hasattr(self, "player") or self.gamemodel.examined:
            if text.startswith('# '):
                text = text[2:]
                self.gamemodel.connection.cm.whisper(text)
            elif text.startswith('whisper '):
                text = text[8:]
                self.gamemodel.connection.cm.whisper(text)
            else:
                if not hasattr(self, "player"):
                    if self.gamemodel.players[0].name == self.gamemodel.connection.username:
                        self.player = self.gamemodel.players[0]
                        self.opplayer = self.gamemodel.players[1]
                    else:
                        self.player = self.gamemodel.players[1]
                        self.opplayer = self.gamemodel.players[0]

                if self.gamemodel.examined:
                    self.opplayer.putMessage(text)
                else:
                    self.player.sendMessage(text)
                self.chatView.addMessage(repr(self.player), text)
        else:
            self.gamemodel.connection.cm.whisper(text)

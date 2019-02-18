import asyncio
from io import StringIO

from pychess.compat import create_task
from pychess.System.Log import log
from pychess.Utils.GameModel import GameModel
from pychess.Utils.Offer import Offer
from pychess.Utils.const import REMOTE, DRAW, WHITE, BLACK, RUNNING, WHITEWON, KILLED, \
    TAKEBACK_OFFER, WAITING_TO_START, BLACKWON, PAUSE_OFFER, PAUSED, \
    RESUME_OFFER, DISCONNECTED, CHAT_ACTION, RESIGNATION, FLAG_CALL, OFFERS, LOCAL, \
    UNFINISHED_STATES, ABORT_OFFER, ACTION_ERROR_NONE_TO_ACCEPT
from pychess.Players.Human import Human
from pychess.Savers import fen as fen_loader
from pychess.ic import GAME_TYPES, TYPE_TOURNAMENT_DIRECTOR


class ICGameModel(GameModel):
    def __init__(self, connection, ficsgame, timemodel):
        assert ficsgame.game_type in GAME_TYPES.values()
        GameModel.__init__(self, timemodel, ficsgame.game_type.variant)
        self.connection = connection
        self.ficsgame = ficsgame
        self.ficsplayers = (ficsgame.wplayer, ficsgame.bplayer)
        self.gmwidg_ready = asyncio.Event()
        self.kibitz_task = None
        self.disconnected = False

        connections = self.connections
        connections[connection.bm].append(connection.bm.connect(
            "boardSetup", self.onBoardSetup))
        connections[connection.bm].append(connection.bm.connect(
            "exGameReset", self.onExGameReset))
        connections[connection.bm].append(connection.bm.connect(
            "gameUndoing", self.onGameUndoing))
        connections[connection.bm].append(connection.bm.connect(
            "timesUpdate", self.onTimesUpdate))
        connections[connection.bm].append(connection.bm.connect(
            "obsGameEnded", self.onGameEnded))
        connections[connection.bm].append(connection.bm.connect(
            "curGameEnded", self.onGameEnded))
        connections[connection.bm].append(connection.bm.connect(
            "gamePaused", self.onGamePaused))
        connections[connection.bm].append(connection.bm.connect(
            "madeExamined", self.onMadeExamined))
        connections[connection.bm].append(connection.bm.connect(
            "madeUnExamined", self.onMadeUnExamined))
        connections[connection.om].append(connection.om.connect(
            "onActionError", self.onActionError))
        connections[connection.cm].append(connection.cm.connect(
            "kibitzMessage", self.onKibitzMessage))
        connections[connection.cm].append(connection.cm.connect(
            "whisperMessage", self.onWhisperMessage))
        connections[connection.cm].append(connection.cm.connect(
            "observers_received", self.onObserversReceived))
        connections[connection].append(connection.connect("disconnected",
                                                          self.onDisconnected))

        rated = "rated" if ficsgame.rated else "unrated"
        # This is in the format that ficsgames.org writes these PGN headers
        ics = "ICC" if self.connection.ICC else "FICS"
        self.tags["Event"] = "%s %s %s game" % (ics, rated, ficsgame.game_type.fics_name)
        self.tags["Site"] = "chessclub.com" if self.connection.ICC else "freechess.org"

    def __repr__(self):
        string = GameModel.__repr__(self)
        string = string.replace("<GameModel", "<ICGameModel")
        fics_game = repr(self.ficsgame)
        string = string.replace(", players=", ", ficsgame=%s, players=" % fics_game)
        return string

    @property
    def display_text(self):
        text = "[ "
        if self.timed:
            text += self.timemodel.display_text + " "
        text += self.ficsgame.display_rated.lower() + " "
        if self.ficsgame.game_type.display_text:
            text += self.ficsgame.game_type.display_text + " "
        return text + "]"

    def __disconnect(self):
        if self.connections is None:
            return
        for obj in self.connections:
            # Humans need to stay connected post-game so that "GUI > Actions" works
            if isinstance(obj, Human):
                continue

            for handler_id in self.connections[obj]:
                if obj.handler_is_connected(handler_id):
                    log.debug("ICGameModel.__disconnect: object=%s handler_id=%s" %
                              (repr(obj), repr(handler_id)))
                    obj.disconnect(handler_id)
        self.disconnected = True

    def ficsplayer(self, player):
        if player.ichandle == self.ficsplayers[0].name:
            return self.ficsplayers[0]
        else:
            return self.ficsplayers[1]

    @property
    def remote_player(self):
        if self.players[0].__type__ == REMOTE:
            return self.players[0]
        else:
            return self.players[1]

    @property
    def remote_ficsplayer(self):
        return self.ficsplayer(self.remote_player)

    def hasGuestPlayers(self):
        for player in self.ficsplayers:
            if player.isGuest():
                return True
        return False

    @property
    def noTD(self):
        for player in self.ficsplayers:
            if TYPE_TOURNAMENT_DIRECTOR in player.titles:
                return False
        return True

    def onExGameReset(self, bm, ficsgame):
        log.debug("ICGameModel.onExGameReset %s" % self)
        if ficsgame == self.ficsgame:
            self.__disconnect()
            self.players[0].end()
            self.players[1].end()

    def onGameUndoing(self, bm, gameno, ply):
        if gameno == self.ficsgame.gameno:
            self.undoMoves(ply)

    def onBoardSetup(self, bm, gameno, fen, wname, bname):
        log.debug("ICGameModel.onBoardSetup: %s %s %s %s %s" % (bm, gameno, fen, wname, bname))
        if gameno != self.ficsgame.gameno or len(self.players) != 2 or self.disconnected:
            return

        # Set up examined game black player
        if "Black" not in self.tags or bname != self.tags["Black"]:
            self.players[BLACK].name = bname
            self.emit("players_changed")

        # Set up examined game white player
        if "White" not in self.tags or wname != self.tags["White"]:
            self.players[WHITE].name = wname
            self.emit("players_changed")

        # Set up examined game position, side to move, castling rights
        if self.boards[-1].asFen() != fen:
            if self.boards[0].asFen().split()[:2] == fen.split()[:2]:
                log.debug("ICGameModel.onBoardSetup: undoing moves %s" % self.moves)
                self.undoMoves(len(self.moves))
                self.ficsgame.move_queue.put_nowait("stm")
                return

            new_position = self.boards[-1].asFen().split()[0] != fen.split()[0]

            # side to move change
            stm_change = self.boards[-1].asFen().split()[1] != fen.split()[1]
            self.status = RUNNING
            self.loadAndStart(
                StringIO(fen),
                fen_loader,
                0,
                -1,
                first_time=False)

            if new_position:
                log.debug('ICGameModel.onBoardSetup: put_nowait("fen"')
                self.ficsgame.move_queue.put_nowait("fen")
                self.emit("game_started")
            elif stm_change:
                log.debug('ICGameModel.onBoardSetup: put_nowait("stm"')
                self.ficsgame.move_queue.put_nowait("stm")

    def update_board(self, gameno, ply, curcol, lastmove, fen, wname,
                     bname, wms, bms):
        log.debug(("ICGameModel.update_board: id=%s self.ply=%s self.players=%s gameno=%s " +
                  "wname=%s bname=%s ply=%s curcol=%s lastmove=%s fen=%s wms=%s bms=%s") %
                  (str(id(self)), str(self.ply), repr(self.players), str(gameno), str(wname), str(bname),
                   str(ply), str(curcol), str(lastmove), str(fen), str(wms), str(bms)))
        if gameno != self.ficsgame.gameno or len(self.players) < 2 or self.disconnected:
            return

        if self.timed:
            log.debug("ICGameModel.update_board: id=%d self.players=%s: updating timemodel" %
                      (id(self), str(self.players)))
            # If game end coming from helper connection before last move made
            # we have to tap() ourselves
            if self.status in (DRAW, WHITEWON, BLACKWON):
                if self.timemodel.ply < ply:
                    self.timemodel.paused = False
                    self.timemodel.tap()
                    self.timemodel.paused = True

            self.timemodel.updatePlayer(WHITE, wms / 1000.)
            self.timemodel.updatePlayer(BLACK, bms / 1000.)

        if ply < self.ply:
            log.debug("ICGameModel.update_board: id=%d self.players=%s \
                      self.ply=%d ply=%d: TAKEBACK" %
                      (id(self), str(self.players), self.ply, ply))
            for offer in list(self.offers.keys()):
                if offer.type == TAKEBACK_OFFER:
                    # There can only be 1 outstanding takeback offer for both players on FICS,
                    # (a counter-offer by the offeree for a takeback for a different number of
                    # moves replaces the initial offer) so we can safely remove all of them
                    del self.offers[offer]

            if len(self.moves) >= self.ply - ply:
                self.undoMoves(self.ply - ply)
            else:
                self.status = RUNNING
                self.loadAndStart(
                    StringIO(fen),
                    fen_loader,
                    0,
                    -1,
                    first_time=False)
                self.emit("game_started")
                curPlayer = self.players[self.curColor]
                curPlayer.resetPosition()

        elif ply > self.ply + 1:
            log.debug("ICGameModel.update_board: id=%d self.players=%s \
                      self.ply=%d ply=%d: FORWARD JUMP" %
                      (id(self), str(self.players), self.ply, ply))
            self.status = RUNNING
            self.loadAndStart(
                StringIO(fen),
                fen_loader,
                0,
                -1,
                first_time=False)
            self.emit("game_started")
            curPlayer = self.players[self.curColor]
            curPlayer.resetPosition()

    def onTimesUpdate(self, bm, gameno, wms, bms):
        if gameno != self.ficsgame.gameno:
            return
        if self.timed:
            self.timemodel.updatePlayer(WHITE, wms / 1000.)
            self.timemodel.updatePlayer(BLACK, bms / 1000.)

    def onMadeExamined(self, bm, gameno):
        self.examined = True

    def onMadeUnExamined(self, bm, gameno):
        self.examined = False

    def onGameEnded(self, bm, ficsgame):
        if ficsgame == self.ficsgame and len(self.players) >= 2:
            log.debug(
                "ICGameModel.onGameEnded: self.players=%s ficsgame=%s" %
                (repr(self.players), repr(ficsgame)))
            self.end(ficsgame.result, ficsgame.reason)

    def setPlayers(self, players):
        GameModel.setPlayers(self, players)
        if self.players[WHITE].icrating:
            self.tags["WhiteElo"] = self.players[WHITE].icrating
        if self.players[BLACK].icrating:
            self.tags["BlackElo"] = self.players[BLACK].icrating

        if (self.connection.username == self.ficsplayers[WHITE].name) and self.ficsplayers[WHITE].isGuest():
            self.tags["White"] += " (Player)"
            self.emit("players_changed")
        if (self.connection.username == self.ficsplayers[BLACK].name) and self.ficsplayers[BLACK].isGuest():
            self.tags["Black"] += " (Player)"
            self.emit("players_changed")

    def onGamePaused(self, bm, gameno, paused):
        if paused:
            self.pause()
        else:
            self.resume()

        # we have to do this here rather than in acceptReceived(), because
        # sometimes FICS pauses/unpauses a game clock without telling us that the
        # original offer was "accepted"/"received", such as when one player offers
        # "pause" and the other player responds not with "accept" but "pause"
        for offer in list(self.offers.keys()):
            if offer.type in (PAUSE_OFFER, RESUME_OFFER):
                del self.offers[offer]

    def onDisconnected(self, connection):
        if self.status in (WAITING_TO_START, PAUSED, RUNNING):
            self.end(KILLED, DISCONNECTED)

    ############################################################################
    # Chat management                                                          #
    ############################################################################

    def onKibitzMessage(self, cm, name, gameno, text):
        @asyncio.coroutine
        def coro():
            if not self.gmwidg_ready.is_set():
                yield from self.gmwidg_ready.wait()
            if gameno != self.ficsgame.gameno:
                return
            self.emit("message_received", name, text)
        self.kibitz_task = create_task(coro())

    def onWhisperMessage(self, cm, name, gameno, text):
        if gameno != self.ficsgame.gameno:
            return
        self.emit("message_received", name, text)

    def onObserversReceived(self, other, gameno, observers):
        if int(gameno) != self.ficsgame.gameno:
            return
        self.emit("observers_received", observers)

    ############################################################################
    # Offer management                                                         #
    ############################################################################

    def offerReceived(self, player, offer):
        log.debug("ICGameModel.offerReceived: offerer=%s %s" %
                  (repr(player), offer))
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else:
            opPlayer = self.players[WHITE]

        if offer.type == CHAT_ACTION:
            opPlayer.putMessage(offer.param)

        elif offer.type in (RESIGNATION, FLAG_CALL):
            self.connection.om.offer(offer)

        elif offer.type in OFFERS:
            if offer not in self.offers:
                log.debug("ICGameModel.offerReceived: %s.offer(%s)" %
                          (repr(opPlayer), offer))
                self.offers[offer] = player
                opPlayer.offer(offer)
            # If the offer was an update to an old one, like a new takebackvalue
            # we want to remove the old one from self.offers
            for offer_ in list(self.offers.keys()):
                if offer.type == offer_.type and offer != offer_:
                    del self.offers[offer_]

    def acceptReceived(self, player, offer):
        log.debug("ICGameModel.acceptReceived: accepter=%s %s" %
                  (repr(player), offer))
        if player.__type__ == LOCAL:
            if offer not in self.offers or self.offers[offer] == player:
                player.offerError(offer, ACTION_ERROR_NONE_TO_ACCEPT)
            else:
                log.debug(
                    "ICGameModel.acceptReceived: connection.om.accept(%s)" %
                    offer)
                self.connection.om.accept(offer)
                del self.offers[offer]

        # We don't handle any ServerPlayer calls here, as the fics server will
        # know automatically if he/she accepts an offer, and will simply send
        # us the result.

    @asyncio.coroutine
    def checkStatus(self):
        pass

    def onActionError(self, om, offer, error):
        self.emit("action_error", offer, error)

    #
    # End
    #

    def end(self, status, reason):
        if self.examined:
            self.connection.bm.unexamine()

        if self.status in UNFINISHED_STATES:
            self.__disconnect()

            if self.isObservationGame():
                self.connection.bm.unobserve(self.ficsgame)
            else:
                self.connection.om.offer(Offer(ABORT_OFFER))
                self.connection.om.offer(Offer(RESIGNATION))

        if status == KILLED:
            GameModel.kill(self, reason)
        else:
            GameModel.end(self, status, reason)

    def terminate(self):
        for obj in self.connections:
            for handler_id in self.connections[obj]:
                if obj.handler_is_connected(handler_id):
                    obj.disconnect(handler_id)

        self.connections = None
        GameModel.terminate(self)
        if self.kibitz_task is not None:
            self.kibitz_task.cancel()

    def goFirst(self):
        self.connection.client.run_command("backward 999")

    def goPrev(self, step=1):
        self.connection.client.run_command("backward %s" % step)

    def goNext(self, step=1):
        self.connection.client.run_command("forward %s" % step)

    def goLast(self):
        self.connection.client.run_command("forward 999")

    def backToMainLine(self):
        self.connection.client.run_command("revert")
